"""Master Tier Configuration — single source of truth for all tier limits and features."""

from app.models.enums import ConversationDirection

TIER_CONFIG = {
    "free": {
        "limits": {
            "chat_generations_per_day": 3,
            "max_screenshots_per_request": 3,
            "profile_audits_per_week": 1,
            "max_photos_per_audit": 3,
            "profile_blueprints_per_week": 0,
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
                ConversationDirection.CHANGE_TOPIC.value,
            ],
        },
    },
    "pro": {
        "limits": {
            "chat_generations_per_day": 20,
            "max_screenshots_per_request": 5,
            "profile_audits_per_week": 3,
            "max_photos_per_audit": 6,
            "profile_blueprints_per_week": 1,
            "max_context_messages": 20,
            "max_custom_hint_chars": 300,
        },
        "features": {
            "voice_dna_enabled": True,
            "custom_hints_enabled": True,
            "include_coach_reasoning": True,
            "advanced_languages_enabled": True,
            "chemistry_tracking_enabled": True,
            "allowed_ui_directions": [
                ConversationDirection.OPENER.value,
                ConversationDirection.QUICK_REPLY.value,
                ConversationDirection.CHANGE_TOPIC.value,
                ConversationDirection.TEASE.value,
                ConversationDirection.REVIVE_CHAT.value,
                ConversationDirection.DE_ESCALATE.value,
            ],
        },
    },
    "premium": {
        "limits": {
            "chat_generations_per_day": 50,
            "max_screenshots_per_request": 7,
            "profile_audits_per_week": 10,
            "max_photos_per_audit": 10,
            "profile_blueprints_per_week": 3,
            "max_context_messages": 40,
            "max_custom_hint_chars": 500,
        },
        "features": {
            "voice_dna_enabled": True,
            "custom_hints_enabled": True,
            "include_coach_reasoning": True,
            "advanced_languages_enabled": True,
            "chemistry_tracking_enabled": True,
            "allowed_ui_directions": [
                ConversationDirection.OPENER.value,
                ConversationDirection.QUICK_REPLY.value,
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
