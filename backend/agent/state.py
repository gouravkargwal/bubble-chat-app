import operator
from typing import Annotated, TypedDict, List, Dict, Any, Optional, Literal

from pydantic import BaseModel, Field

# ---------- Structured outputs ----------

StrategyLabel = Literal[
    "PUSH-PULL",
    "FRAME CONTROL",
    "SOFT CLOSE",
    "VALUE ANCHOR",
    "PATTERN INTERRUPT",
    "HONEST FRAME",
]


class ChatBubble(BaseModel):
    sender: Literal["user", "them"] = Field(
        description="'user' if right of screen midline, 'them' if left of midline"
    )
    quoted_context: str = Field(
        description="If present, the grey/indented quoted box text at the top of the bubble; "
        'otherwise "".'
    )
    actual_new_message: str = Field(
        description="The bottom-most fresh text that was just typed in this bubble."
    )


class AnalystOutput(BaseModel):
    visual_transcript: List[ChatBubble] = Field(default_factory=list)
    visual_hooks: List[str] = Field(
        default_factory=list,
        description="List 3-4 specific physical or environmental details from the photos.",
    )
    photo_persona: str = Field(
        default="",
        description=(
            "1-3 words for the curated persona/aesthetic her photos project "
            "(e.g. 'rebel/edgy', 'soft romantic', 'influencer-polished'). The vibe she "
            "CHOSE, not a judgment of her looks. Empty if no photos."
        ),
    )
    detected_dialect: Literal["ENGLISH", "HINDI", "HINGLISH"]
    their_tone: str
    their_effort: str
    conversation_temperature: str
    archetype_reasoning: str = Field(
        default="",
        description=(
            "2-3 sentences justifying the dimension scores below, citing her message structure "
            "(word count, question vs statement, emoji use, effort) and/or profile content."
        ),
    )
    # Constrained personality dimensions (see agent/nodes_v2/_personality.py).
    warmth: Literal["guarded", "neutral", "warm"] = "neutral"
    playfulness: Literal["earnest", "balanced", "playful"] = "balanced"
    engagement: Literal["low", "medium", "high"] = "medium"
    traditionalism: Literal["modern", "mixed", "traditional"] = "mixed"
    intent: Literal["exploring", "open", "long_term"] = "open"
    # Derived in code from the dimensions above; not chosen by the LLM. Retained
    # for logging + Phase 4/5 learning continuity.
    detected_archetype: str = Field(default="THE WARM/STEADY")
    top_hooks: List[str] = Field(
        default_factory=list,
        description="Chat: three distinct hooks; first must match key_detail. Profile: empty.",
    )
    key_detail: str
    person_name: str = Field(
        default="unknown", description="First name if visible, else 'unknown'."
    )
    stage: str = Field(default="early_talking", description="Conversation stage.")
    their_last_message: str = Field(
        default="", description="Paraphrase of the other person's last message."
    )
    user_last_move: str = Field(
        default="",
        description=(
            "Chat only: 1-sentence read of the USER's own most recent message — was it high/low effort "
            "and is her current tone a reaction to it. Empty if no user message in the thread."
        ),
    )
    inbound_image: Literal["none", "selfie_of_her", "object_or_scene"] = Field(
        default="none",
        description=(
            "Did SHE send an image as a chat message: 'selfie_of_her', 'object_or_scene', or 'none'."
        ),
    )
    inbound_image_detail: Optional[str] = Field(
        default="",
        description="Short noun phrase naming the memory-worthy subject of an image she sent.",
    )
    durable_facts: List[str] = Field(
        default_factory=list,
        description="Atomic, durable, third-person facts about her, extracted for long-term memory.",
    )
    # --- Video content scoring (consumed by the video-export pipeline) ---
    hook_type: str = Field(
        default="strategy",
        description="Video hook classification: 'roast', 'gap', 'outcome', or 'strategy'.",
    )
    time_gap_signal: str = Field(
        default="",
        description="Visible time-stamp gap between messages, e.g. '3 hours'. Empty if none.",
    )
    viral_tier: str = Field(
        default="medium",
        description="Video potential tier: 'low', 'medium', 'high', or 'viral'.",
    )
    viral_reasoning: str = Field(
        default="",
        description="1 sentence explaining the viral_tier classification.",
    )


class StrategyOutput(BaseModel):
    wrong_moves: List[str]
    right_energy: str
    hook_point: str
    recommended_strategy_label: StrategyLabel


class ReplyOption(BaseModel):
    text: str = Field(
        description=(
            "The outbound message. Follow dialect enforcement and formatting rules from the system prompt "
            "(e.g., lowercase, no proper punctuation)."
        )
    )
    strategy_label: StrategyLabel = Field(
        description="Dominant tactic for this reply; must match what the text actually does."
    )
    is_recommended: bool = Field(
        description="True for exactly one reply — the single best option to send."
    )
    coach_reasoning: str = Field(
        description=(
            "One short sentence explaining why this angle fits context and archetype, "
            "addressed directly to the user as coaching advice. Write in second person "
            "('you') — never refer to the sender by any character/persona name."
        )
    )


class WriterOutput(BaseModel):
    replies: List[ReplyOption]


class AuditorOutput(BaseModel):
    is_cringe: bool
    feedback: str


class BouncerOutput(BaseModel):
    is_valid_chat: bool
    reason: str


# ---------- LangGraph agent state ----------


class AgentState(TypedDict):
    # Inputs
    image_bytes: str
    vision_out: Dict[str, Any]
    direction: str
    custom_hint: str
    user_id: str
    conversation_id: str | None
    voice_dna_dict: Dict[str, Any]
    conversation_context_dict: Dict[str, Any]
    ocr_hint_text: (
        str  # last OCR text from hybrid stitch, used for semantic memory search
    )

    # Bouncer state
    is_valid_chat: bool
    bouncer_reason: str

    # Node outputs
    analysis: Optional[AnalystOutput]
    strategy: Optional[StrategyOutput]
    drafts: Optional[WriterOutput]
    core_lore: str
    past_memories: str  # deprecated — kept for backward compat
    tier_1_raw_exchanges: str  # Tier 1: FIFO sliding window of last N raw messages
    tier_2_summary: str  # Tier 2: compressed narrative of recent conversation arc
    precomputed_queries: list[str]  # Vision-generated RAG search variants (zero-latency)
    # OCR output is now structured so ownership can be handled deterministically.
    raw_ocr_text: List["RawOcrTextItem"]
    detected_contradictions: List[str]

    # Auditor state
    is_cringe: bool
    auditor_feedback: str
    revision_count: int
    safe_replies: list[dict]
    failed_assignments: list[dict]

    # Token usage + exact gemini_pricing cost per LangChain call (concatenated by LangGraph)
    gemini_usage_log: Annotated[list[dict[str, Any]], operator.add]


class RawOcrTextItem(TypedDict):
    """
    Strict OCR item schema for one bubble.

    `sender` is ALWAYS the bubble anchor based on horizontal alignment:
    - left-aligned bubble => "them"
    - right-aligned bubble => "user"

    `actual_new_message` is the bold/solid fresh text below any quoted (faded) block.
    It may be empty for reply-only bubbles that show only referenced context.
    `quoted_context` is the quoted/referenced top block text (or null if none).
    """

    sender: Literal["user", "them"]
    actual_new_message: str
    quoted_context: str | None
    is_reply: bool
