"""API request/response schemas."""

from pydantic import BaseModel, Field


# Auth
class AuthResponse(BaseModel):
    token: str
    user_id: str
    expires_at: int
    email: str | None = None
    display_name: str | None = None
    is_new_user: bool = False
    trial_tier: str | None = None


class FirebaseAuthRequest(BaseModel):
    firebase_token: str = Field(
        ..., description="Firebase ID token from the client SDK"
    )
    device_id: str | None = Field(
        default=None,
        description="Optional device ID to migrate anonymous data to the Firebase account",
    )


# Vision
class VisionRequest(BaseModel):
    image: str | None = Field(
        default=None, description="Single base64 screenshot (backward compat)"
    )
    images: list[str] | None = Field(
        default=None, description="Multiple base64 screenshots"
    )
    direction: str = Field(default="quick_reply")
    custom_hint: str | None = Field(default=None, max_length=200)
    conversation_id: str | None = None


class VisionResponse(BaseModel):
    replies: list[str]
    person_name: str | None = None
    stage: str = "early_talking"
    interaction_id: str
    usage_remaining: int
    conversation_id: str


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
    daily_limit: int  # 0 = unlimited
    daily_used: int
    is_premium: bool
    tier: str = "free"
    allowed_directions: list[str] = []
    max_screenshots: int = 1
    custom_hints: bool = False
    tier_expires_at: int | None = None
    bonus_replies: int = 0
    total_replies_generated: int = 0  # Total interactions created by this user
    total_replies_copied: int = 0  # Total interactions where user copied a reply


# Conversations
class ConversationItem(BaseModel):
    id: str
    person_name: str
    stage: str
    tone_trend: str
    interaction_count: int


class ConversationListResponse(BaseModel):
    conversations: list[ConversationItem]


# Referral
class ReferralInfoResponse(BaseModel):
    referral_code: str
    total_referrals: int
    bonus_replies_earned: int
    max_referrals: int = 10


class ApplyReferralRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=8)


class ApplyReferralResponse(BaseModel):
    bonus_granted: int
    new_total_bonus: int


# Billing
class VerifyPurchaseRequest(BaseModel):
    purchase_token: str
    product_id: str
    order_id: str | None = None


class VerifyPurchaseResponse(BaseModel):
    is_valid: bool
    premium_until: int | None = None  # unix timestamp


class BillingStatusResponse(BaseModel):
    is_premium: bool
    tier: str = "free"
    product_id: str | None = None
    expires_at: int | None = None
    auto_renewing: bool = False


# Promo
class ApplyPromoRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)


class ApplyPromoResponse(BaseModel):
    tier_granted: str
    duration_days: int
    expires_at: int  # unix timestamp


# History
class HistoryItemResponse(BaseModel):
    id: str
    person_name: str | None = None
    direction: str
    custom_hint: str | None = None
    replies: list[str]
    copied_index: int | None = None
    created_at: int  # unix timestamp


class HistoryListResponse(BaseModel):
    items: list[HistoryItemResponse]


# User Preferences
class VibeBreakdownItem(BaseModel):
    name: str
    percentage: float


class UserPreferencesResponse(BaseModel):
    total_ratings: int
    has_enough_data: bool
    vibe_breakdown: list[VibeBreakdownItem]
    preferred_length: str = "medium"
