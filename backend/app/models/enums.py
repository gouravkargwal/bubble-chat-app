"""Enums for type-safe constants."""

from enum import Enum


class ConversationDirection(str, Enum):
    """Conversation direction types for chat generation."""

    OPENER = "opener"
    QUICK_REPLY = "quick_reply"
    CHANGE_TOPIC = "change_topic"
    TEASE = "tease"
    REVIVE_CHAT = "revive_chat"
    GET_NUMBER = "get_number"
    ASK_OUT = "ask_out"
    DE_ESCALATE = "de_escalate"
