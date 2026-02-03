"""API client for PromptElo community server."""

import httpx
from typing import Optional

from config import get_server_url, get_user_id, get_timeout


class PromptEloAPIError(Exception):
    """Error from PromptElo API."""
    pass


def score_prompt(prompt: str) -> dict:
    """Submit a prompt to the community server for novelty scoring.

    Args:
        prompt: The prompt text to score

    Returns:
        Dict with novelty scoring results:
        {
            "novelty": {
                "novelty_score": float,  # 0-1
                "percentile": float,  # 0-100
                "similar_count": int,
                "is_novel": bool
            },
            "total_prompts": int,
            "timestamp": str
        }

    Raises:
        PromptEloAPIError: If the API call fails
    """
    server_url = get_server_url()
    user_id = get_user_id()
    timeout = get_timeout()

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{server_url}/api/v1/score",
                json={
                    "prompt": prompt,
                    "user_id": user_id
                }
            )

            if response.status_code == 429:
                raise PromptEloAPIError("Rate limit exceeded. Please try again later.")

            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise PromptEloAPIError("Request timed out. Server may be unavailable.")
    except httpx.ConnectError:
        raise PromptEloAPIError("Could not connect to PromptElo server.")
    except httpx.HTTPStatusError as e:
        raise PromptEloAPIError(f"API error: {e.response.status_code}")


def get_stats() -> dict:
    """Get global statistics from the community server.

    Returns:
        Dict with global stats:
        {
            "total_prompts": int,
            "unique_users": int,
            "avg_novelty_score": float,
            "percentile_thresholds": {...},
            "top_novelty_scores": [...]
        }

    Raises:
        PromptEloAPIError: If the API call fails
    """
    server_url = get_server_url()
    timeout = get_timeout()

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{server_url}/api/v1/stats")
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise PromptEloAPIError("Request timed out. Server may be unavailable.")
    except httpx.ConnectError:
        raise PromptEloAPIError("Could not connect to PromptElo server.")
    except httpx.HTTPStatusError as e:
        raise PromptEloAPIError(f"API error: {e.response.status_code}")


def check_health() -> dict:
    """Check the health of the community server.

    Returns:
        Dict with health status:
        {
            "status": str,
            "database_connected": bool,
            "embedding_service": bool,
            "version": str
        }

    Raises:
        PromptEloAPIError: If the API call fails
    """
    server_url = get_server_url()

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{server_url}/api/v1/health")
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise PromptEloAPIError("Health check timed out.")
    except httpx.ConnectError:
        raise PromptEloAPIError("Could not connect to PromptElo server.")
    except httpx.HTTPStatusError as e:
        raise PromptEloAPIError(f"Health check failed: {e.response.status_code}")
