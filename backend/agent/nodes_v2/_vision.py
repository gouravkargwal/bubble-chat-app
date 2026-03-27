"""
Node 1: vision_node (pass-through)

The main VisionNode LLM call is executed in the v2 API endpoint *before* stitching.
This node only converts the already-parsed `VisionNodeOutput` stored in the
LangGraph state into:
  - `analysis` (AnalystOutput)
  - `raw_ocr_text` (normalized OCR bubble objects)

No LLM calls happen in this file anymore.
"""

from typing import Any, cast

import structlog
from pydantic import BaseModel, Field

from agent.nodes_v2._shared import (
    normalize_raw_ocr_text,
)
from agent.state import AgentState, AnalystOutput, ChatBubble

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class VisionNodeOutput(BaseModel):
    """Combined output of bouncer + OCR + analyst in a single call."""

    # Bouncer fields
    is_valid_chat: bool = Field(
        description="true if this image is a chat/dating app screenshot, false otherwise."
    )
    bouncer_reason: str = Field(description="Short reason for the validity decision.")

    # OCR fields — only populated when is_valid_chat is true
    raw_ocr_text: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of bubble objects extracted verbatim. Each has: "
            "sender ('user'=right-aligned, 'them'=left-aligned), "
            "actual_new_message (bottom-most fresh solid text below any quoted block; "
            "may be empty for reply-only bubbles), "
            "quoted_context (quoted/referenced top block text or null), "
            "is_reply (true iff quoted_context present)."
        ),
    )

    # Analyst fields — only populated when is_valid_chat is true
    visual_transcript: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of ChatBubble dicts: sender, quoted_context, actual_new_message.",
    )
    visual_hooks: list[str] = Field(
        default_factory=list,
        description="3-4 specific physical or environmental details from photos.",
    )
    detected_dialect: str = Field(
        default="ENGLISH",
        description="ENGLISH, HINDI, or HINGLISH based on her most recent message.",
    )
    their_tone: str = Field(default="neutral")
    their_effort: str = Field(default="medium")
    conversation_temperature: str = Field(default="warm")
    archetype_reasoning: str = Field(
        default="",
        description=(
            "2-3 sentence reasoning for archetype selection. If visual evidence in the "
            "chat screenshot contradicts Core Lore and you prioritize visuals, explicitly "
            "state that contradiction and that visual evidence overrode Lore."
        ),
    )
    detected_archetype: str = Field(default="THE WARM/STEADY")
    key_detail: str = Field(default="")
    person_name: str = Field(default="unknown")
    stage: str = Field(default="early_talking")
    their_last_message: str = Field(default="")


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


def vision_node(state: AgentState) -> dict:
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
    past_memories = state.get("past_memories", "") or ""

    logger.info(
        "llm_lifecycle",
        stage="vision_node_start_pass_through",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        is_valid_chat=bool(out.is_valid_chat),
        person_name=out.person_name,
    )

    if not out.is_valid_chat:
        return {
            "is_valid_chat": False,
            "bouncer_reason": out.bouncer_reason,
            "analysis": None,
            "raw_ocr_text": [],
            "core_lore": core_lore,
            "past_memories": past_memories,
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
        detected_dialect=out.detected_dialect,  # type: ignore[arg-type]
        their_tone=out.their_tone,
        their_effort=out.their_effort,
        conversation_temperature=out.conversation_temperature,
        archetype_reasoning=out.archetype_reasoning,
        detected_archetype=out.detected_archetype,
        key_detail=out.key_detail,
        person_name=out.person_name,
        stage=out.stage,
        their_last_message=out.their_last_message,
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
        "past_memories": past_memories,
    }
