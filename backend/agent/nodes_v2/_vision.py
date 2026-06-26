"""
Node 1: vision_node (pass-through)

The main VisionNode LLM call is executed in the v2 API endpoint *before* stitching.
This node only converts the already-parsed `VisionNodeOutput` stored in the
LangGraph state into:
  - `analysis` (AnalystOutput)
  - `raw_ocr_text` (normalized OCR bubble objects)

No LLM calls happen in this file anymore.
"""

from typing import Any, Literal, Optional, cast

import structlog
from pydantic import BaseModel, Field

from agent.nodes_v2._personality import (
    Engagement,
    Intent,
    Playfulness,
    Traditionalism,
    Warmth,
)
from agent.nodes_v2._shared import (
    normalize_raw_ocr_text,
)
from agent.state import AgentState, AnalystOutput, ChatBubble

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class VisionNodeOutput(BaseModel):
    """Combined structural output of bouncer + OCR + analyst in a single call."""

    # Bouncer fields
    is_valid_chat: bool = Field(
        description="True only if the images show a valid chat thread or dating profile."
    )
    bouncer_reason: str = Field(
        description="Brief validation reason for the bouncer gate decision."
    )

    # App & sender reasoning — chain-of-thought fields
    detected_app: str = Field(
        default="unknown",
        description="Name of the hosting dating or messaging application identified from layout.",
    )
    sender_signals_used: str = Field(
        default="",
        description="Brief step-by-step reasoning explaining the visual anchors used to isolate message senders.",
    )

    # OCR fields
    raw_ocr_text: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Array of extracted raw message objects containing structural attributes.",
    )

    # Analyst fields
    visual_transcript: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sequential list of transcript bubbles mapped 1:1 to chronological reality.",
    )
    visual_hooks: list[str] = Field(
        default_factory=list,
        description="List of 3-4 highly specific physical, environmental, or contextual details from photos.",
    )
    photo_persona: str = Field(
        default="",
        description="1-3 words defining her chosen self-presentation aesthetic or curated persona vibe.",
    )
    detected_dialect: str = Field(
        default="ENGLISH",
        description="The dominant language dialect or language mix detected across the visible profile copy.",
    )
    their_tone: str = Field(
        default="neutral",
        description="The primary emotional tone displayed by her copy.",
    )
    their_effort: str = Field(
        default="medium",
        description="The qualitative effort tier of her profile copy or thread text.",
    )
    conversation_temperature: str = Field(
        default="warm", description="The current engagement openness level."
    )
    archetype_reasoning: str = Field(
        default="",
        description="2-3 sentences justifying the assigned personality metric scores below.",
    )

    # Personality dimensions
    warmth: Warmth = Field(
        default="neutral",
        description="Metric capturing if she is guarded, neutral, or warm and receptive.",
    )
    playfulness: Playfulness = Field(
        default="balanced",
        description="Metric capturing if her tone is earnest, balanced, or playful and sarcastic.",
    )
    engagement: Engagement = Field(
        default="medium",
        description="Metric capturing if her textual investment level is low, medium, or high.",
    )
    traditionalism: Traditionalism = Field(
        default="mixed",
        description="Metric capturing if her background values lean modern, mixed, or traditional.",
    )
    intent: Intent = Field(
        default="open",
        description="Metric capturing if her relationship goal signals exploring, open, or long_term.",
    )

    detected_archetype: str = Field(default="THE WARM/STEADY")
    top_hooks: list[str] = Field(
        default_factory=list,
        description="Array of exactly three distinct conversation hook options derived from the current turn.",
    )
    key_detail: str = Field(
        default="",
        description="The single absolute best text prompt or conversational anchor selected for banter value.",
    )
    person_name: str = Field(
        default="unknown", description="First name of the profile target."
    )
    stage: str = Field(
        default="early_talking",
        description="Calculated lifecycle position of the relationship.",
    )
    their_last_message: str = Field(
        default="",
        description="Relational context paraphrase of her latest message, or holistic profile vibe summary.",
    )
    user_last_move: str = Field(
        default="",
        description="One-sentence evaluation of the user's latest text turn and her clear reaction to it.",
    )
    inbound_image: Literal["none", "selfie_of_her", "object_or_scene"] = Field(
        default="none",
        description="Classification of any graphic media file transmitted as an active message bubble by her.",
    )
    inbound_image_detail: Optional[str] = Field(
        default="",
        description="Short noun phrase capturing the long-term durable subject matter of her incoming message photo.",
    )
    durable_facts: list[str] = Field(
        default_factory=list,
        description="0-5 atomic, long-term third-person lifestyle facts explicitly gathered about her.",
    )


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


async def vision_node(state: AgentState) -> dict:
    """
    Pass-through node: the endpoint already ran the full VisionNode LLM call and
    stored the parsed `VisionNodeOutput` under `state["vision_out"]`.

    This node only:
      - converts `VisionNodeOutput` -> `AnalystOutput`
      - normalizes `raw_ocr_text`
    """
    trace_id = state.get("trace_id", "")
    user_id = state.get("user_id", "")
    conversation_id = state.get("conversation_id") or ""
    direction = state.get("direction", "")

    out_raw = state.get("vision_out") or {}
    out = VisionNodeOutput.model_validate(out_raw)

    core_lore = state.get("core_lore", "") or ""
    tier_1_raw = state.get("tier_1_raw_exchanges", "") or ""
    tier_2_summary = state.get("tier_2_summary", "") or ""

    logger.info(
        "llm_lifecycle",
        stage="vision_node_start_pass_through",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        is_valid_chat=bool(out.is_valid_chat),
        person_name=out.person_name,
        detected_app=out.detected_app,
        sender_signals_used=out.sender_signals_used,
    )

    if not out.is_valid_chat:
        return {
            "is_valid_chat": False,
            "bouncer_reason": out.bouncer_reason,
            "analysis": None,
            "raw_ocr_text": [],
            "core_lore": core_lore,
            "tier_1_raw_exchanges": tier_1_raw,
            "tier_2_summary": tier_2_summary,
        }

    # Build AnalystOutput from VisionNodeOutput fields
    visual_transcript: list[ChatBubble] = []
    for bubble in out.visual_transcript:
        if isinstance(bubble, ChatBubble):
            visual_transcript.append(bubble)
        elif isinstance(bubble, dict):
            visual_transcript.append(
                ChatBubble(
                    sender=bubble.get("sender", "them"),
                    quoted_context=bubble.get("quoted_context") or "",
                    actual_new_message=bubble.get("actual_new_message", ""),
                )
            )

    analysis = AnalystOutput(
        visual_transcript=visual_transcript,
        visual_hooks=out.visual_hooks,
        photo_persona=out.photo_persona,
        detected_dialect=out.detected_dialect,  # type: ignore[arg-type]
        their_tone=out.their_tone,
        their_effort=out.their_effort,
        conversation_temperature=out.conversation_temperature,
        archetype_reasoning=out.archetype_reasoning,
        warmth=out.warmth,
        playfulness=out.playfulness,
        engagement=out.engagement,
        traditionalism=out.traditionalism,
        intent=out.intent,
        detected_archetype=out.detected_archetype,
        top_hooks=out.top_hooks,
        key_detail=out.key_detail,
        person_name=out.person_name,
        stage=out.stage,
        their_last_message=out.their_last_message,
        user_last_move=out.user_last_move,
        inbound_image=out.inbound_image,
        inbound_image_detail=out.inbound_image_detail,
        durable_facts=out.durable_facts,
    )

    raw_ocr_text = normalize_raw_ocr_text(out.raw_ocr_text)

    logger.info(
        "llm_lifecycle",
        stage="vision_node_complete_pass_through",
        trace_id=trace_id,
        is_valid_chat=True,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        bubble_count=len(raw_ocr_text),
        visual_transcript_count=len(visual_transcript),
        visual_hooks_count=len(out.visual_hooks or []),
        detected_archetype=out.detected_archetype,
        detected_dialect=out.detected_dialect,
        conversation_temperature=out.conversation_temperature,
        analysis_stage=out.stage,
        person_name=out.person_name,
    )

    return {
        "is_valid_chat": True,
        "bouncer_reason": out.bouncer_reason,
        "raw_ocr_text": raw_ocr_text,
        "analysis": analysis,
        "core_lore": core_lore,
        "tier_1_raw_exchanges": tier_1_raw,
        "tier_2_summary": tier_2_summary,
    }
