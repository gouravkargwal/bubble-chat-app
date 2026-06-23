"""Master Tier Configuration — 4 plans, credits-based quota.

Plans:
  - free:  ₹0   — 15 signup credits on first open, then 2/day forever.
  - crush: ₹99  — 60 credits, resets every 7 days.
  - match: ₹179 — 150 credits, resets every 30 days. (Most Popular ⭐)
  - rizz:  ₹299 — 250 credits, resets every 30 days. Unlocks Get Number + Ask Out.

Credit costs per action:
  - chat_generation:   1 credit
  - profile_audit:     5 credits
  - profile_blueprint: 8 credits
"""

from app.config import settings
from app.models.enums import ConversationDirection


def voice_dna_feature_active(tier_config: dict) -> bool:
    return settings.voice_dna_enabled and tier_config["features"]["voice_dna_enabled"]


# Credit costs per action.
CREDIT_COSTS = {
    "chat_generation": 1,
    "profile_audit": 5,
    "profile_blueprint": 8,
}

# Free tier: 15 signup credits on first open, then 2/day forever.
FREE_SIGNUP_CREDITS = 15
FREE_DAILY_CREDITS = 2

# Credits and billing period per paid plan.
BILLING_CREDITS = {
    "crush": 60,  # ₹99/week
    "match": 150,  # ₹179/month
    "rizz": 250,  # ₹299/month
}

BILLING_PERIOD_DAYS = {
    "crush": 7,
    "match": 30,
    "rizz": 30,
}

TIER_CONFIG = {
    "free": {
        "limits": {
            "daily_credits": FREE_DAILY_CREDITS,
            "signup_credits": FREE_SIGNUP_CREDITS,
            "max_screenshots_per_request": 2,
            "max_photos_per_audit": 3,
            "max_context_messages": 10,
            "max_custom_hint_chars": 0,
        },
        "features": {
            "voice_dna_enabled": False,
            "custom_hints_enabled": False,
            "include_coach_reasoning": False,
            "advanced_languages_enabled": False,
            "chemistry_tracking_enabled": False,
            "allowed_ui_directions": [
                ConversationDirection.OPENER.value,
                ConversationDirection.QUICK_REPLY.value,
            ],
        },
    },
    "crush": {
        "limits": {
            "daily_credits": 0,
            "period_credits": BILLING_CREDITS["crush"],
            "max_screenshots_per_request": 5,
            "max_photos_per_audit": 6,
            "max_context_messages": 20,
            "max_custom_hint_chars": 300,
        },
        "features": {
            "voice_dna_enabled": False,
            "custom_hints_enabled": True,
            "include_coach_reasoning": True,
            "advanced_languages_enabled": True,
            "chemistry_tracking_enabled": True,
            "allowed_ui_directions": [
                ConversationDirection.OPENER.value,
                ConversationDirection.QUICK_REPLY.value,
                ConversationDirection.KEEP_PLAYFUL.value,
                ConversationDirection.CHANGE_TOPIC.value,
                ConversationDirection.TEASE.value,
                ConversationDirection.REVIVE_CHAT.value,
                ConversationDirection.DE_ESCALATE.value,
            ],
        },
    },
    "match": {
        "limits": {
            "daily_credits": 0,
            "period_credits": BILLING_CREDITS["match"],
            "max_screenshots_per_request": 5,
            "max_photos_per_audit": 6,
            "max_context_messages": 25,
            "max_custom_hint_chars": 300,
        },
        "features": {
            "voice_dna_enabled": False,
            "custom_hints_enabled": True,
            "include_coach_reasoning": True,
            "advanced_languages_enabled": True,
            "chemistry_tracking_enabled": True,
            "allowed_ui_directions": [
                ConversationDirection.OPENER.value,
                ConversationDirection.QUICK_REPLY.value,
                ConversationDirection.KEEP_PLAYFUL.value,
                ConversationDirection.CHANGE_TOPIC.value,
                ConversationDirection.TEASE.value,
                ConversationDirection.REVIVE_CHAT.value,
                ConversationDirection.DE_ESCALATE.value,
            ],
        },
    },
    "rizz": {
        "limits": {
            "daily_credits": 0,
            "period_credits": BILLING_CREDITS["rizz"],
            "max_screenshots_per_request": 7,
            "max_photos_per_audit": 10,
            "max_context_messages": 40,
            "max_custom_hint_chars": 500,
        },
        "features": {
            "voice_dna_enabled": False,
            "custom_hints_enabled": True,
            "include_coach_reasoning": True,
            "advanced_languages_enabled": True,
            "chemistry_tracking_enabled": True,
            "allowed_ui_directions": [
                ConversationDirection.OPENER.value,
                ConversationDirection.QUICK_REPLY.value,
                ConversationDirection.KEEP_PLAYFUL.value,
                ConversationDirection.CHANGE_TOPIC.value,
                ConversationDirection.TEASE.value,
                ConversationDirection.REVIVE_CHAT.value,
                ConversationDirection.GET_NUMBER.value,
                ConversationDirection.ASK_OUT.value,
                ConversationDirection.DE_ESCALATE.value,
            ],
        },
    },
}
