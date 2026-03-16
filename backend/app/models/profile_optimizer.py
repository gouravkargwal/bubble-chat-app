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
            "A short hook label inspired by this photo, "
            "e.g. 'Parent approval', 'Wedding plus one', 'Adventure brag with receipts'."
        ),
    )
    hinge_prompt: str = Field(
        ...,
        description=(
            "A ready-to-paste Hinge prompt answer for this photo (max 150 chars). "
            "Hinge prompts are conversational and invite a reply. "
            "e.g. 'The one thing I'll never shut up about' → 'Finding the best hole-in-the-wall spots in every city I visit.'"
        ),
    )
    aisle_prompt: str = Field(
        ...,
        description=(
            "A ready-to-paste Aisle prompt answer for this photo. "
            "Aisle skews relationship-focused — be warm, genuine, show depth. "
            "e.g. 'A story behind this photo' → 'Spent a week solo in Kyoto. Came back knowing I want someone to share the next one with.'"
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
        description="Optimized slots in final display order — one per available photo (max 6).",
        min_length=1,
        max_length=6,
    )
    overall_theme: str = Field(
        ...,
        description="Short sentence describing the overarching vibe of this profile.",
    )
    bio: str = Field(
        ...,
        max_length=500,
        description=(
            "A punchy, high-status bio (max 500 chars) that works across all dating apps. "
            "Blend 2-3 specific fun facts with a confident, low-investment tone. "
            "No cringe, no desperation."
        ),
    )
    universal_prompts: list[UniversalPrompt] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Three hook objects that can be re-used as prompts or answers across apps.",
    )
