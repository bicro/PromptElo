"""FastAPI community server for PromptElo embedding storage and novelty scoring."""

import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import (
    GlobalStats,
    HealthResponse,
    NoveltyResult,
    ScoreRequest,
    ScoreResponse,
)
from database import (
    init_db,
    close_db,
    store_embedding,
    find_similar_embeddings,
    get_total_count,
    get_novelty_percentile,
    get_global_stats,
    check_connection,
)
from embeddings import (
    init_embedding_client,
    close_embedding_client,
    get_embedding,
    calculate_novelty_score,
    check_embedding_service,
)

# Version
VERSION = "0.1.0"

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))  # requests per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # window in seconds

# In-memory rate limit tracking (use Redis in production for multi-instance)
rate_limit_store: dict[str, list[float]] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(client_ip: str) -> tuple[bool, int]:
    """Check if client is within rate limit.

    Returns:
        Tuple of (is_allowed, remaining_requests)
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if t > window_start
    ]

    # Check limit
    current_requests = len(rate_limit_store[client_ip])
    if current_requests >= RATE_LIMIT_REQUESTS:
        return False, 0

    # Record this request
    rate_limit_store[client_ip].append(now)
    return True, RATE_LIMIT_REQUESTS - current_requests - 1


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    await init_embedding_client()
    await init_db()
    yield
    # Shutdown
    await close_db()
    await close_embedding_client()


# Create FastAPI app
app = FastAPI(
    title="PromptElo API",
    description="Community embedding server for prompt novelty scoring",
    version=VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests."""
    # Skip rate limiting for health check
    if request.url.path == "/api/v1/health":
        return await call_next(request)

    client_ip = get_client_ip(request)
    is_allowed, remaining = check_rate_limit(client_ip)

    if not is_allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "retry_after": RATE_LIMIT_WINDOW
            },
            headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + RATE_LIMIT_WINDOW),
                "Retry-After": str(RATE_LIMIT_WINDOW)
            }
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


@app.post("/api/v1/score", response_model=ScoreResponse)
async def score_prompt(request: ScoreRequest) -> ScoreResponse:
    """Score a prompt for novelty and store its embedding.

    This endpoint:
    1. Generates an embedding for the prompt using OpenAI
    2. Searches for similar prompts in the database
    3. Calculates a novelty score based on similarity
    4. Stores the embedding for future comparisons
    5. Returns the novelty score and percentile ranking
    """
    try:
        # Generate embedding
        embedding = await get_embedding(request.prompt)

        # Find similar embeddings
        similar = await find_similar_embeddings(embedding, threshold=0.70)

        # Calculate novelty score
        novelty_score = calculate_novelty_score(similar)

        # Store the embedding
        await store_embedding(
            embedding=embedding,
            novelty_score=novelty_score,
            user_id=request.user_id
        )

        # Get percentile ranking
        percentile = await get_novelty_percentile(novelty_score)

        # Get total count
        total = await get_total_count()

        # Determine if highly novel (top 15%)
        is_novel = percentile >= 85

        return ScoreResponse(
            novelty=NoveltyResult(
                novelty_score=novelty_score,
                percentile=percentile,
                similar_count=len(similar),
                is_novel=is_novel
            ),
            total_prompts=total,
            timestamp=datetime.utcnow()
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/v1/stats", response_model=GlobalStats)
async def get_stats() -> GlobalStats:
    """Get global statistics about the prompt database.

    Returns aggregate statistics without exposing any actual prompts.
    """
    try:
        stats = await get_global_stats()
        return GlobalStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring and load balancers."""
    db_healthy = await check_connection()
    embedding_healthy = await check_embedding_service()

    status = "healthy" if (db_healthy and embedding_healthy) else "degraded"

    return HealthResponse(
        status=status,
        database_connected=db_healthy,
        embedding_service=embedding_healthy,
        version=VERSION
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "PromptElo API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
