"""Tier configuration — single source of truth for feature gating."""

from datetime import datetime, timezone

TIER_HIERARCHY = {"free": 0, "crush": 1, "match": 2, "rizz": 3}


def get_effective_tier(user) -> str:
    now_aware = datetime.now(timezone.utc)
    tier = user.tier or "free"
    if tier == "free":
        return tier

    if user.tier_expires_at:
        expires_at = user.tier_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now_aware:
            return "free"

    return tier


def has_tier_access(user_tier: str, required_tier: str) -> bool:
    return TIER_HIERARCHY.get(user_tier, 0) >= TIER_HIERARCHY.get(required_tier, 0)


# Product ID → tier mapping (cookd_premium subscription, 3 prepaid base plans)
# Play sends both "subscription_id:base_plan_id" and bare "subscription_id" formats.
PRODUCT_TIER_MAP = {
    "cookd_premium:crush-weekly":  "crush",
    "cookd_premium:match-monthly": "match",
    "cookd_premium:rizz-monthly":  "rizz",
    # bare subscription ID fallback (some webhook events omit base plan)
    "cookd_premium": "crush",
}
