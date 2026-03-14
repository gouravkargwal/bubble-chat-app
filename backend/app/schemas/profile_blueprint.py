"""Pydantic schemas for ProfileBlueprint API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class BlueprintSlotResponse(BaseModel):
    """Response schema for a single blueprint slot."""

    id: str
    photo_id: str
    slot_number: int = Field(ge=1, le=6)
    role: str
    caption: str
    universal_hook: str
    image_url: str = Field(description="Full URL to the image")


class UniversalPromptResponse(BaseModel):
    """Response schema for a universal prompt."""

    category: str
    suggested_text: str


class ProfileBlueprintResponse(BaseModel):
    """Response schema for a profile blueprint with nested slots."""

    id: str
    user_id: str
    overall_theme: str
    tinder_bio: str
    bumble_bio: str
    created_at: datetime
    slots: list[BlueprintSlotResponse]
    universal_prompts: list[UniversalPromptResponse] | None = None


class ProfileBlueprintListResponse(BaseModel):
    """Response schema for a list of profile blueprints."""

    items: list[ProfileBlueprintResponse]
    total_count: int
    limit: int
    offset: int