"""Pydantic models for the Brutal Profile Auditor feature."""

from enum import Enum

from pydantic import BaseModel, Field


class PhotoTier(str, Enum):
    """Tier classification for a profile photo."""

    GOD_TIER = "GOD_TIER"
    FILLER = "FILLER"
    GRAVEYARD = "GRAVEYARD"


class PhotoFeedback(BaseModel):
    """Model representing feedback for a single profile photo."""

    photo_id: str
    score: int = Field(..., ge=1, le=10)
    tier: PhotoTier | None = None  # computed server-side; not returned by LLM
    brutal_feedback: str
    improvement_tip: str


class AuditResponse(BaseModel):
    """Aggregated result for a full profile audit."""

    total_analyzed: int
    passed_count: int
    is_hard_reset: bool
    # Archetype + roast are per-audit, not per-photo.
    archetype_title: str | None = None
    roast_summary: str | None = None
    photos: list[PhotoFeedback]
