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
        description="'user' if right-aligned, 'them' if left-aligned"
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
        description="List 3-4 specific physical or environmental details from the photos."
    )
    detected_dialect: Literal["ENGLISH", "HINDI", "HINGLISH"]
    their_tone: str
    their_effort: str
    conversation_temperature: str
    archetype_reasoning: str = Field(
        description=(
            "FIRST count her words, check her message structure (question? statement? emoji-only?), "
            "and note her effort level. THEN reason about which archetype fits based on the "
            "MESSAGE STRUCTURE RULES, not tone labels."
        )
    )
    detected_archetype: str = Field(
        description=(
            "Based strictly on the reasoning above, select EXACTLY ONE: "
            "'THE BANTER GIRL', 'THE INTELLECTUAL', 'THE WARM/STEADY', "
            "'THE GUARDED/TESTER', 'THE EAGER/DIRECT', or 'THE LOW-INVESTMENT'."
        )
    )
    key_detail: str
    person_name: str = Field(default="unknown", description="First name if visible, else 'unknown'.")
    stage: str = Field(default="early_talking", description="Conversation stage.")
    their_last_message: str = Field(default="", description="Paraphrase of the other person's last message.")


class StrategyOutput(BaseModel):
    wrong_moves: List[str]
    right_energy: str
    hook_point: str
    recommended_strategy_label: StrategyLabel


class ReplyOption(BaseModel):
    text: str
    strategy_label: StrategyLabel
    is_recommended: bool
    coach_reasoning: str


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
    direction: str
    custom_hint: str
    user_id: str
    conversation_id: str | None
    voice_dna_dict: Dict[str, Any]
    conversation_context_dict: Dict[str, Any]
    ocr_hint_text: str  # last OCR text from hybrid stitch, used for semantic memory search

    # Bouncer state
    is_valid_chat: bool
    bouncer_reason: str

    # Node outputs
    analysis: Optional[AnalystOutput]
    strategy: Optional[StrategyOutput]
    drafts: Optional[WriterOutput]
    core_lore: str
    past_memories: str
    # OCR output is now structured so ownership can be handled deterministically.
    raw_ocr_text: List["RawOcrTextItem"]

    # Auditor state
    is_cringe: bool
    auditor_feedback: str
    revision_count: int

    # Token usage + exact gemini_pricing cost per LangChain call (concatenated by LangGraph)
    gemini_usage_log: Annotated[list[dict[str, Any]], operator.add]


class RawOcrTextItem(TypedDict):
    """
    Strict OCR item schema for one bubble.

    `sender` is ALWAYS the bubble anchor based on horizontal alignment:
    - left-aligned bubble => "them"
    - right-aligned bubble => "user"

    `actual_new_message` is the bold/solid fresh text below any quoted (faded) block.
    `quoted_context` is the quoted (faded) top block text (or null if none).
    """

    sender: Literal["user", "them"]
    actual_new_message: str
    quoted_context: str | None
    is_reply: bool
