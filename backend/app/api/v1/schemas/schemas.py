"""API request/response schemas."""

from pydantic import BaseModel, Field


# Auth
class AuthResponse(BaseModel):
    token: str
    user_id: str
    expires_at: int
    email: str | None = None
    display_name: str | None = None


class FirebaseAuthRequest(BaseModel):
    firebase_token: str = Field(..., description="Firebase ID token from the client SDK")
    device_id: str | None = Field(
        default=None,
        description="Optional device ID to migrate anonymous data to the Firebase account",
    )


# Vision
class VisionRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded screenshot (JPEG)")
    direction: str = Field(default="quick_reply")
    custom_hint: str | None = Field(default=None, max_length=200)


class VisionResponse(BaseModel):
    replies: list[str]
    person_name: str | None = None
    stage: str = "early_talking"
    interaction_id: str
    usage_remaining: int


# Tracking
class CopyTrackRequest(BaseModel):
    interaction_id: str
    reply_index: int = Field(..., ge=0, le=3)


class RatingTrackRequest(BaseModel):
    interaction_id: str
    reply_index: int = Field(..., ge=0, le=3)
    is_positive: bool


# Usage
class UsageResponse(BaseModel):
    daily_limit: int
    daily_used: int
    is_premium: bool
    premium_expires_at: int | None = None


# Conversations
class ConversationItem(BaseModel):
    id: str
    person_name: str
    stage: str
    tone_trend: str
    interaction_count: int


class ConversationListResponse(BaseModel):
    conversations: list[ConversationItem]
