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
    contextual_hook: str = Field(
        ...,
        description=(
            "A short, versatile hook inspired by this photo that can power many prompts, "
            "e.g. 'Parent approval', 'Wedding plus one', 'Adventure brag with receipts'."
        ),
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


class UniversalPrompt(BaseModel):
    """Cross-app hook object that can be turned into prompts on any dating app."""

    category: str = Field(
        ...,
        description='Short label for the hook, e.g. "Parent Approval", "Low-Key Flex", "Wingman Energy".',
    )
    suggested_text: str = Field(
        ...,
        description="Concrete example text the user can adapt into any in-app prompt.",
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
    tinder_bio: str = Field(
        ...,
        max_length=500,
        description="Short, punchy Tinder bio. Low-investment and high-status.",
    )
    bumble_bio: str = Field(
        ...,
        description=(
            "Bumble 'About Me' style text with ~3 fun, specific facts that feel playful and approachable."
        ),
    )
    universal_prompts: list[UniversalPrompt] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Three hook objects that can be re-used as prompts or answers across apps.",
    )

