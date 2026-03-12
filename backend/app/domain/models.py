from enum import StrEnum
from dataclasses import dataclass, field


class Direction(StrEnum):
    OPENER = "opener"
    QUICK_REPLY = "quick_reply"
    CHANGE_TOPIC = "change_topic"
    TEASE = "tease"
    GET_NUMBER = "get_number"
    ASK_OUT = "ask_out"
    REVIVE_CHAT = "revive_chat"


class Stage(StrEnum):
    NEW_MATCH = "new_match"
    OPENING = "opening"
    EARLY_TALKING = "early_talking"
    BUILDING_CHEMISTRY = "building_chemistry"
    DEEP_CONNECTION = "deep_connection"
    RELATIONSHIP = "relationship"
    STALLED = "stalled"
    ARGUMENT = "argument"


class Tone(StrEnum):
    EXCITED = "excited"
    PLAYFUL = "playful"
    FLIRTY = "flirty"
    NEUTRAL = "neutral"
    DRY = "dry"
    UPSET = "upset"
    TESTING = "testing"
    VULNERABLE = "vulnerable"
    SARCASTIC = "sarcastic"


class Effort(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Temperature(StrEnum):
    HOT = "hot"
    WARM = "warm"
    LUKEWARM = "lukewarm"
    COLD = "cold"


class ToneTrend(StrEnum):
    WARMING = "warming"
    STABLE = "stable"
    COOLING = "cooling"


@dataclass
class AnalysisResult:
    their_last_message: str = ""
    who_texted_last: str = "unclear"
    their_tone: str = "neutral"
    their_effort: str = "medium"
    conversation_temperature: str = "warm"
    stage: str = "early_talking"
    person_name: str = "unknown"
    key_detail: str = ""
    what_they_want: str = ""


@dataclass
class StrategyResult:
    wrong_moves: list[str] = field(default_factory=list)
    right_energy: str = ""
    hook_point: str = ""


@dataclass
class VisualTranscriptItem:
    side: str
    sender: str
    message_text: str


@dataclass
class ParsedLlmResponse:
    visual_transcript: list[VisualTranscriptItem]
    analysis: AnalysisResult
    strategy: StrategyResult
    replies: list[str]


@dataclass
class ConversationContext:
    person_name: str = "unknown"
    stage: str = "new_match"
    tone_trend: str = "stable"
    topics_worked: list[str] = field(default_factory=list)
    topics_failed: list[str] = field(default_factory=list)
    interaction_count: int = 0
    recent_summaries: list[str] = field(default_factory=list)


@dataclass
class VoiceDNA:
    avg_reply_length: float = 0.0
    emoji_frequency: float = 0.0
    common_words: list[str] = field(default_factory=list)
    punctuation_style: str = "casual"
    capitalization: str = "lowercase"
    preferred_length: str = "medium"
    sample_count: int = 0
    top_vibes: list[str] = field(default_factory=list)
    disliked_vibes: list[str] = field(default_factory=list)
    recent_organic_messages: list[str] = field(default_factory=list)
    semantic_profile: str | None = None


@dataclass
class PromptPayload:
    system_prompt: str
    user_prompt: str
    temperature: float
