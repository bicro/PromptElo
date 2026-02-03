"""PostgreSQL + pgvector database operations for PromptElo."""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import asyncpg
from asyncpg import Pool

# Connection pool
_pool: Optional[Pool] = None

# Embedding dimension for text-embedding-3-small
EMBEDDING_DIM = 1536


async def init_db() -> Pool:
    """Initialize the database connection pool and create tables."""
    global _pool

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    _pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        command_timeout=60
    )

    async with _pool.acquire() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Create prompts table with embedding column
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS prompt_embeddings (
                id SERIAL PRIMARY KEY,
                embedding vector({EMBEDDING_DIM}) NOT NULL,
                novelty_score FLOAT NOT NULL,
                user_id VARCHAR(64),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Create index for fast similarity search (IVFFlat for better performance at scale)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS prompt_embeddings_embedding_idx
            ON prompt_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

        # Create index for user_id lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS prompt_embeddings_user_id_idx
            ON prompt_embeddings (user_id)
        """)

        # Create stats table for caching global statistics
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS global_stats_cache (
                id INTEGER PRIMARY KEY DEFAULT 1,
                total_prompts INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0,
                avg_novelty_score FLOAT DEFAULT 0.5,
                percentile_50 FLOAT DEFAULT 0.5,
                percentile_75 FLOAT DEFAULT 0.65,
                percentile_90 FLOAT DEFAULT 0.78,
                percentile_95 FLOAT DEFAULT 0.85,
                percentile_99 FLOAT DEFAULT 0.92,
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                CHECK (id = 1)
            )
        """)

        # Initialize stats cache if empty
        await conn.execute("""
            INSERT INTO global_stats_cache (id)
            VALUES (1)
            ON CONFLICT (id) DO NOTHING
        """)

    return _pool


async def close_db():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> Pool:
    """Get the database connection pool."""
    if _pool is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _pool


async def store_embedding(
    embedding: list[float],
    novelty_score: float,
    user_id: Optional[str] = None
) -> int:
    """Store a prompt embedding and return its ID."""
    pool = get_pool()

    async with pool.acquire() as conn:
        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        result = await conn.fetchrow(
            """
            INSERT INTO prompt_embeddings (embedding, novelty_score, user_id)
            VALUES ($1::vector, $2, $3)
            RETURNING id
            """,
            embedding_str,
            novelty_score,
            user_id
        )
        return result["id"]


async def find_similar_embeddings(
    embedding: list[float],
    threshold: float = 0.85,
    limit: int = 100
) -> list[dict]:
    """Find similar embeddings using cosine similarity.

    Args:
        embedding: The query embedding vector
        threshold: Minimum cosine similarity (0-1) to consider a match
        limit: Maximum number of results to return

    Returns:
        List of dicts with id, similarity, and novelty_score
    """
    pool = get_pool()
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    async with pool.acquire() as conn:
        # Use cosine distance (1 - cosine_similarity), so lower is more similar
        # threshold of 0.85 similarity = distance of 0.15
        distance_threshold = 1 - threshold

        rows = await conn.fetch(
            """
            SELECT
                id,
                1 - (embedding <=> $1::vector) as similarity,
                novelty_score
            FROM prompt_embeddings
            WHERE (embedding <=> $1::vector) < $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            embedding_str,
            distance_threshold,
            limit
        )

        return [
            {
                "id": row["id"],
                "similarity": float(row["similarity"]),
                "novelty_score": float(row["novelty_score"])
            }
            for row in rows
        ]


async def get_total_count() -> int:
    """Get the total number of stored embeddings."""
    pool = get_pool()

    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM prompt_embeddings")
        return result or 0


async def get_novelty_percentile(novelty_score: float) -> float:
    """Calculate the percentile ranking for a given novelty score."""
    pool = get_pool()

    async with pool.acquire() as conn:
        # Count how many prompts have a lower novelty score
        result = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE novelty_score < $1) as lower_count,
                COUNT(*) as total_count
            FROM prompt_embeddings
            """,
            novelty_score
        )

        if result["total_count"] == 0:
            return 50.0  # Default to median if no data

        return (result["lower_count"] / result["total_count"]) * 100


async def get_global_stats() -> dict:
    """Get global statistics about all prompts."""
    pool = get_pool()

    async with pool.acquire() as conn:
        # Get basic counts
        counts = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_prompts,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(novelty_score) as avg_novelty
            FROM prompt_embeddings
        """)

        # Get percentile thresholds
        percentiles = await conn.fetchrow("""
            SELECT
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY novelty_score) as p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY novelty_score) as p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY novelty_score) as p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY novelty_score) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY novelty_score) as p99
            FROM prompt_embeddings
        """)

        # Get top novelty scores (without exposing prompts)
        top_scores = await conn.fetch("""
            SELECT novelty_score
            FROM prompt_embeddings
            ORDER BY novelty_score DESC
            LIMIT 10
        """)

        return {
            "total_prompts": counts["total_prompts"] or 0,
            "unique_users": counts["unique_users"] or 0,
            "avg_novelty_score": float(counts["avg_novelty"] or 0.5),
            "percentile_thresholds": {
                "p50": float(percentiles["p50"] or 0.5),
                "p75": float(percentiles["p75"] or 0.65),
                "p90": float(percentiles["p90"] or 0.78),
                "p95": float(percentiles["p95"] or 0.85),
                "p99": float(percentiles["p99"] or 0.92),
            },
            "top_novelty_scores": [float(row["novelty_score"]) for row in top_scores]
        }


async def check_connection() -> bool:
    """Check if the database connection is healthy."""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        return False
