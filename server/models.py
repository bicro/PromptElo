"""Pydantic models for the PromptElo API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    """Request body for scoring a prompt."""
    prompt: str = Field(..., min_length=1, max_length=10000, description="The prompt to score")
    user_id: Optional[str] = Field(None, description="Optional anonymous user ID for tracking personal stats")


class NoveltyResult(BaseModel):
    """Novelty scoring result from embedding comparison."""
    novelty_score: float = Field(..., ge=0, le=1, description="Novelty score from 0 to 1")
    percentile: float = Field(..., ge=0, le=100, description="Percentile ranking among all prompts")
    similar_count: int = Field(..., ge=0, description="Number of similar prompts found")
    is_novel: bool = Field(..., description="Whether the prompt is considered highly novel")


class ScoreResponse(BaseModel):
    """Response body for prompt scoring."""
    novelty: NoveltyResult
    total_prompts: int = Field(..., description="Total prompts in the database")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GlobalStats(BaseModel):
    """Global statistics about the prompt database."""
    total_prompts: int
    unique_users: int
    avg_novelty_score: float
    percentile_thresholds: dict[str, float]  # e.g., {"p50": 0.45, "p90": 0.78}
    top_novelty_scores: list[float]  # Top 10 novelty scores (no prompts exposed)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database_connected: bool
    embedding_service: bool
    version: str
