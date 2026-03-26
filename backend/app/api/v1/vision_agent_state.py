"""Shared LangGraph ↔ API mapping for the v2 vision pipeline (no v1 endpoint)."""

from __future__ import annotations

import dataclasses
from uuid import uuid4

from app.domain.models import (
    AnalysisResult,
    ConversationContext,
    ParsedLlmResponse,
    ReplyOption as DomainReplyOption,
    StrategyResult,
    VisualTranscriptItem,
    VoiceDNA,
)


def _build_agent_initial_state(
    image_base64: str,
    direction: str,
    custom_hint: str,
    user_id: str,
    conversation_id: str | None,
    voice_dna: VoiceDNA | None,
    conversation_context: ConversationContext | None,
) -> dict:
    """Build initial AgentState for the LangGraph v2 agent."""
    voice_dict = dataclasses.asdict(voice_dna) if voice_dna else {}
    context_dict = dataclasses.asdict(conversation_context) if conversation_context else {}
    return {
        "trace_id": str(uuid4()),
        "image_bytes": image_base64,
        "vision_out": {},
        "direction": direction,
        "custom_hint": custom_hint,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "voice_dna_dict": voice_dict,
        "conversation_context_dict": context_dict,
        "is_valid_chat": True,
        "bouncer_reason": "",
        "analysis": None,
        "strategy": None,
        "drafts": None,
        "is_cringe": False,
        "auditor_feedback": "",
        "revision_count": 0,
        "core_lore": "",
        "past_memories": "",
        "raw_ocr_text": [],
        "detected_contradictions": [],
        "ocr_hint_text": "",
        "gemini_usage_log": [],
    }


def _parsed_from_agent_state(final_state: dict) -> ParsedLlmResponse:
    """Map final agent state to ParsedLlmResponse for persistence and response."""
    analysis_out = final_state["analysis"]
    strategy_out = final_state["strategy"]
    drafts = final_state["drafts"]

    visual_transcript = []
    for bubble in analysis_out.visual_transcript:
        visual_transcript.append(
            VisualTranscriptItem(
                side="right" if bubble.sender == "user" else "left",
                sender=bubble.sender,
                quoted_context=bubble.quoted_context,
                actual_new_message=bubble.actual_new_message,
                is_reply_to_user=False,
            )
        )

    analysis = AnalysisResult(
        their_last_message=getattr(analysis_out, "their_last_message", "") or "",
        who_texted_last="unclear",
        their_tone=analysis_out.their_tone,
        their_effort=analysis_out.their_effort,
        conversation_temperature=analysis_out.conversation_temperature,
        stage=getattr(analysis_out, "stage", "early_talking") or "early_talking",
        person_name=getattr(analysis_out, "person_name", "unknown") or "unknown",
        key_detail=analysis_out.key_detail,
        what_they_want="",
        detected_dialect=analysis_out.detected_dialect,
        their_actual_new_message=(
            next(
                (
                    b.actual_new_message
                    for b in reversed(analysis_out.visual_transcript)
                    if b.sender == "them"
                ),
                "",
            )
            if analysis_out.visual_transcript
            else ""
        ),
        detected_archetype=analysis_out.detected_archetype,
        archetype_reasoning=analysis_out.archetype_reasoning,
    )

    strategy = StrategyResult(
        wrong_moves=strategy_out.wrong_moves,
        right_energy=strategy_out.right_energy,
        hook_point=strategy_out.hook_point,
    )

    replies = [
        DomainReplyOption(
            text=r.text,
            strategy_label=r.strategy_label,
            is_recommended=r.is_recommended,
            coach_reasoning=r.coach_reasoning,
        )
        for r in drafts.replies[:4]
    ]

    return ParsedLlmResponse(
        visual_transcript=visual_transcript,
        analysis=analysis,
        strategy=strategy,
        replies=replies,
    )
