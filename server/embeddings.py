"""OpenAI embedding integration for PromptElo."""

import os
from typing import Optional

import httpx

# OpenAI API configuration
OPENAI_API_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# HTTP client for making requests
_client: Optional[httpx.AsyncClient] = None


async def init_embedding_client():
    """Initialize the HTTP client for OpenAI API calls."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)


async def close_embedding_client():
    """Close the HTTP client."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


def get_client() -> httpx.AsyncClient:
    """Get the HTTP client."""
    if _client is None:
        raise RuntimeError("Embedding client not initialized. Call init_embedding_client() first.")
    return _client


async def get_embedding(text: str) -> list[float]:
    """Get embedding vector for a text string using OpenAI API.

    Args:
        text: The text to embed (will be truncated if too long)

    Returns:
        List of floats representing the embedding vector

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        httpx.HTTPStatusError: If the API call fails
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    # Truncate text if too long (OpenAI has a token limit)
    # text-embedding-3-small supports up to 8191 tokens
    # Rough estimate: 4 characters per token
    max_chars = 8191 * 4
    if len(text) > max_chars:
        text = text[:max_chars]

    client = get_client()

    response = await client.post(
        OPENAI_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": EMBEDDING_MODEL,
            "input": text,
            "encoding_format": "float"
        }
    )
    response.raise_for_status()

    data = response.json()
    return data["data"][0]["embedding"]


def calculate_novelty_score(similar_embeddings: list[dict]) -> float:
    """Calculate novelty score based on similar embeddings found.

    The novelty score is inversely related to how similar the prompt is
    to existing prompts in the database.

    Args:
        similar_embeddings: List of similar embeddings with similarity scores

    Returns:
        Novelty score between 0 and 1 (1 = highly novel)
    """
    if not similar_embeddings:
        # No similar prompts found = highly novel
        return 1.0

    # Calculate weighted average similarity
    # More weight to the most similar prompts
    total_weight = 0
    weighted_similarity = 0

    for i, emb in enumerate(similar_embeddings[:10]):  # Top 10 most similar
        weight = 1.0 / (i + 1)  # Decreasing weight
        weighted_similarity += emb["similarity"] * weight
        total_weight += weight

    avg_similarity = weighted_similarity / total_weight if total_weight > 0 else 0

    # Convert similarity to novelty (higher similarity = lower novelty)
    # Use a non-linear transformation to make the score more meaningful
    # Similarity of 1.0 (exact match) -> novelty of 0
    # Similarity of 0.85 (threshold) -> novelty of ~0.5
    # Similarity of 0.7 -> novelty of ~0.8

    if avg_similarity >= 0.95:
        # Very similar - likely duplicate or near-duplicate
        novelty = 0.1 * (1 - avg_similarity) / 0.05
    elif avg_similarity >= 0.85:
        # Similar - common pattern
        novelty = 0.1 + 0.4 * (0.95 - avg_similarity) / 0.10
    elif avg_similarity >= 0.7:
        # Somewhat similar
        novelty = 0.5 + 0.3 * (0.85 - avg_similarity) / 0.15
    else:
        # Quite different
        novelty = 0.8 + 0.2 * (0.7 - avg_similarity) / 0.7

    # Also factor in the count of similar prompts
    count_factor = 1.0 / (1.0 + len(similar_embeddings) * 0.05)
    novelty = novelty * (0.7 + 0.3 * count_factor)

    return max(0.0, min(1.0, novelty))


async def check_embedding_service() -> bool:
    """Check if the embedding service is available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False

    try:
        # Make a minimal API call to check connectivity
        client = get_client()
        response = await client.post(
            OPENAI_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": "test",
                "encoding_format": "float"
            }
        )
        return response.status_code == 200
    except Exception:
        return False
