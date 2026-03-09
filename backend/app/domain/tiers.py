"""Tier configuration — single source of truth for feature gating."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TierConfig:
    name: str
    daily_limit: int  # 0 = unlimited
    allowed_directions: list[str] = field(default_factory=list)
    custom_hints: bool = False
    voice_dna: bool = False
    conversation_memory: bool = False
    max_conversations: int = 0  # 0 = unlimited
    max_screenshots: int = 1  # max images per single request
    prompt_variant: str = "minimal"
    max_output_tokens: int = 1500


# Direction definitions
ALL_DIRECTIONS = [
    "quick_reply", "keep_playful", "get_number",
    "ask_out", "go_deeper", "change_topic",
]

FREE_DIRECTIONS = ["quick_reply", "keep_playful"]

TIERS: dict[str, TierConfig] = {
    "free": TierConfig(
        name="Free",
        daily_limit=5,
        allowed_directions=FREE_DIRECTIONS,
        custom_hints=False,
        voice_dna=False,
        conversation_memory=False,
        max_conversations=3,
        max_screenshots=1,
        prompt_variant="minimal",
        max_output_tokens=1500,
    ),
    "premium": TierConfig(
        name="Premium",
        daily_limit=50,
        allowed_directions=ALL_DIRECTIONS,
        custom_hints=True,
        voice_dna=False,
        conversation_memory=True,
        max_conversations=10,
        max_screenshots=3,
        prompt_variant="default",
        max_output_tokens=2000,
    ),
    "pro": TierConfig(
        name="Pro",
        daily_limit=0,  # unlimited
        allowed_directions=ALL_DIRECTIONS,
        custom_hints=True,
        voice_dna=True,
        conversation_memory=True,
        max_conversations=0,  # unlimited
        max_screenshots=5,
        prompt_variant="default",
        max_output_tokens=2500,
    ),
}

TIER_HIERARCHY = {"free": 0, "premium": 1, "pro": 2}


def get_tier_config(tier: str) -> TierConfig:
    return TIERS.get(tier, TIERS["free"])


def _utc_now_naive() -> "datetime":
    """Return current UTC time as a naive datetime (consistent with DB storage)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_effective_tier(user) -> str:
    """Get user's effective tier, considering expiration."""
    tier = user.tier or "free"
    if tier == "free":
        return tier

    now = _utc_now_naive()

    # Check tier expiry (for promo/trial tiers)
    if user.tier_expires_at and user.tier_expires_at < now:
        return "free"

    # Also check premium billing expiry
    if user.premium_expires_at and user.premium_expires_at < now:
        return "free"

    return tier


def has_tier_access(user_tier: str, required_tier: str) -> bool:
    """Check if user_tier meets the required_tier level."""
    return TIER_HIERARCHY.get(user_tier, 0) >= TIER_HIERARCHY.get(required_tier, 0)


# Product ID → tier mapping
PRODUCT_TIER_MAP = {
    "cookd_premium_weekly": "premium",
    "cookd_premium_monthly": "premium",
    "cookd_pro_weekly": "pro",
    "cookd_pro_monthly": "pro",
}
