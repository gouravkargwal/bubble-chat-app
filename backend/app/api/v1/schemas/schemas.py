"""API request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ConversationDirection


# Auth
class AuthResponse(BaseModel):
    token: str
    user_id: str
    expires_at: int
    email: str | None = None
    display_name: str | None = None
    is_new_user: bool = False


class FirebaseAuthRequest(BaseModel):
    firebase_token: str = Field(
        ..., description="Firebase ID token from the client SDK"
    )
    device_id: str | None = Field(
        default=None,
        description="Optional device ID to migrate anonymous data to the Firebase account",
    )
    google_provider_id: str | None = Field(
        default=None,
        description=(
            "Stable Google provider ID from Firebase providerData[].uid where "
            "providerId == 'google.com'. Used as the primary key for user_quotas."
        ),
    )


# Vision
class VisionRequest(BaseModel):
    image: str | None = Field(
        default=None, description="Single base64 screenshot (backward compat)"
    )
    images: list[str] | None = Field(
        default=None, description="Multiple base64 screenshots"
    )
    direction: ConversationDirection = Field(default=ConversationDirection.QUICK_REPLY)
    custom_hint: str | None = Field(default=None, max_length=200)
    conversation_id: str | None = None


class ReplyOptionPayload(BaseModel):
    text: str
    strategy_label: str
    is_recommended: bool
    coach_reasoning: str = ""  # Empty string for free tier users


class VisionResponse(BaseModel):
    replies: list[ReplyOptionPayload]
    person_name: str | None = None
    stage: str = "early_talking"
    interaction_id: str
    usage_remaining: int
    conversation_id: str


# Hybrid stitch confirmation (cross-platform chat resolution)
class SuggestedMatchContextPreview(BaseModel):
    her_last_message: str
    your_last_reply: str
    ai_memory_note: str


class SuggestedMatch(BaseModel):
    person_name: str
    conversation_id: str
    last_active: str
    context_preview: SuggestedMatchContextPreview


class RequiresUserConfirmation(BaseModel):
    status: Literal["REQUIRES_USER_CONFIRMATION"]
    suggested_match: SuggestedMatch


class CalibrationRequest(BaseModel):
    images: list[str] = Field(..., description="Base64 screenshots for calibration")


class CalibrationResponse(BaseModel):
    messages_extracted: int
    success: bool


class ResolveConversationRequest(BaseModel):
    user_id: str
    suggested_conversation_id: str
    is_match: bool
    new_ocr_text: str


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
    weekly_used: int = 0  # Usage in current week
    monthly_used: int = 0  # Usage in current month
    weekly_audits_used: int = 0  # Profile audits used this week
    weekly_blueprints_used: int = 0  # Profile blueprints generated this week
    is_premium: bool
    tier: str = "free"
    allowed_directions: list[str] = []
    max_screenshots: int = 1
    custom_hints: bool = False
    tier_expires_at: int | None = None
    god_mode_expires_at: int | None = None  # UTC timestamp for 24-hour referral reward
    bonus_replies: int = 0
    total_replies_generated: int = 0  # Total interactions created by this user
    total_replies_copied: int = 0  # Total interactions where user copied a reply
    # New tier config structure
    limits: dict[str, int] = {}
    features: dict[str, bool | list[str]] = {}
    billing_period: str = (
        "daily"  # "daily", "weekly", or "monthly" - extracted from product_id
    )


# Conversations
class ConversationItem(BaseModel):
    id: str
    person_name: str
    stage: str
    tone_trend: str
    interaction_count: int


class ConversationListResponse(BaseModel):
    items: list[ConversationItem]
    total_count: int
    limit: int
    offset: int


# Referral
class ReferralInfoResponse(BaseModel):
    referral_code: str
    total_referrals: int
    bonus_replies_earned: int
    max_referrals: int = 10


class ApplyReferralRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=8)
    device_id: str | None = None  # Android device ID for anti-fraud check


class ApplyReferralResponse(BaseModel):
    tier_granted: str
    duration_hours: int
    expires_at: int | None = None  # unix timestamp (UTC)


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


# History
class HistoryItemResponse(BaseModel):
    id: str
    person_name: str | None = None
    direction: str
    custom_hint: str | None = None
    replies: list[ReplyOptionPayload]
    copied_index: int | None = None
    created_at: int  # unix timestamp
    user_organic_text: str | None = None


class HistoryListResponse(BaseModel):
    items: list[HistoryItemResponse]
    total_count: int
    limit: int
    offset: int


# User Preferences
class VibeBreakdownItem(BaseModel):
    name: str
    percentage: float


class UserPreferencesResponse(BaseModel):
    total_ratings: int
    has_enough_data: bool
    vibe_breakdown: list[VibeBreakdownItem]
    preferred_length: str = "medium"


# Profile Auditor History
class AuditedPhotoItem(BaseModel):
    id: str
    score: int
    tier: str
    brutal_feedback: str
    improvement_tip: str
    # Optional overall roast line from the audit session.
    roast_summary: str | None = None
    image_url: str
    created_at: int  # unix timestamp


class AuditedPhotoListResponse(BaseModel):
    items: list[AuditedPhotoItem]
    total_count: int
    limit: int
    offset: int


# Profile Audit Job (async processing)
from app.models.profile_auditor import AuditResponse  # noqa: E402


class AuditJobSubmitResponse(BaseModel):
    job_id: str
    status: str = "pending"


class AuditJobStatusResponse(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress_current: int = 0
    progress_total: int = 0
    progress_step: str = "uploading"  # uploading, reading, dedup_check, analyzing, saving, done
    error: str | None = None
    result: AuditResponse | None = None
