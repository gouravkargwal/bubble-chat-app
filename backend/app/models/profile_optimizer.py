"""Pydantic models for the Profile Optimizer feature."""

from pydantic import BaseModel, Field


class OptimizedSlot(BaseModel):
    """Single optimized profile slot chosen from audited photos."""

    photo_id: str = Field(
        ...,
        description="ID of the audited photo chosen for this slot. Must match an `audited_photos.id`.",
    )
    slot_number: int = Field(
        ...,
        ge=1,
        le=6,
        description="Position of this photo in the final profile (1-6).",
    )
    role: str = Field(
        ...,
        description='Creative role label for this slot, e.g. "The Anchor", "The Social Proof".',
    )
    caption: str = Field(
        ...,
        description="Witty, high-status caption text to pair with this photo.",
    )
    hinge_prompt_question: str = Field(
        ...,
        description="Suggested Hinge prompt question that matches this photo and overall vibe.",
    )
    hinge_prompt_answer: str = Field(
        ...,
        description="Suggested answer to the Hinge prompt, written in the user's voice.",
    )
    coach_reasoning: str = Field(
        ...,
        description="Short explanation from the coach about why this photo and slot were chosen.",
    )
    # Populated by backend after LLM call so the Android app can render the image directly.
    storage_url: str | None = Field(
        default=None,
        description="Absolute URL to the stored image derived from `storage_path`.",
    )


class ProfileBlueprint(BaseModel):
    """Full optimized profile blueprint for the user."""

    slots: list[OptimizedSlot] = Field(
        ...,
        description="Exactly six optimized slots in final display order.",
        min_length=6,
        max_length=6,
    )
    overall_theme: str = Field(
        ...,
        description="Short sentence describing the overarching vibe of this profile.",
    )

