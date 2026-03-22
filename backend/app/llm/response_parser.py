"""Parse structured LLM output into domain objects.

This module assumes Gemini's native Structured JSON Outputs are enabled.
We expect the raw model output to be a single valid JSON object that
matches our response schema, and we do not perform markdown or regex
fallback extraction.
"""

import json
import re

import structlog

from app.domain.models import (
    AnalysisResult,
    ParsedLlmResponse,
    StrategyResult,
    ReplyOption,
)

logger = structlog.get_logger()


def parse_llm_response(raw: str) -> ParsedLlmResponse:
    """Parse LLM output into structured response.

    With structured outputs enabled on the Gemini API, we expect `raw` to be
    a valid JSON string matching our response schema. Any JSON decode failure
    is treated as a hard error.
    """
    return _parse_json(raw)


def _parse_json(text: str) -> ParsedLlmResponse:
    """Parse a JSON response into structured domain objects."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(
            "parse_json_decode_error",
            error=str(e),
            text_preview=text[:500],
        )
        raise

    # Parse visual transcript (forces the AI to map spatial layout)
    transcript_data = data.get("visual_transcript", [])
    visual_transcript = []
    for item in transcript_data:
        if (
            isinstance(item, dict)
            and "side" in item
            and "sender" in item
            and "actual_new_message" in item
            and "is_reply_to_user" in item
        ):
            from app.domain.models import VisualTranscriptItem

            visual_transcript.append(
                VisualTranscriptItem(
                    side=str(item.get("side")),
                    sender=str(item.get("sender")),
                    quoted_context=str(item.get("quoted_context", "")),
                    actual_new_message=str(item.get("actual_new_message")),
                    is_reply_to_user=bool(item.get("is_reply_to_user")),
                )
            )

    # Handle error response
    if "error" in data:
        raise ValueError(f"LLM returned error: {data['error']}")

    # Parse analysis
    analysis_data = data.get("analysis", {})
    analysis = AnalysisResult(
        their_last_message=analysis_data.get("their_last_message", ""),
        who_texted_last=analysis_data.get("who_texted_last", "unclear"),
        their_tone=analysis_data.get("their_tone", "neutral"),
        their_effort=analysis_data.get("their_effort", "medium"),
        conversation_temperature=analysis_data.get("conversation_temperature", "warm"),
        stage=analysis_data.get("stage", "early_talking"),
        person_name=analysis_data.get("person_name", "unknown"),
        key_detail=analysis_data.get("key_detail", ""),
        what_they_want=analysis_data.get("what_they_want", ""),
        detected_dialect=analysis_data.get("detected_dialect"),
        their_actual_new_message=analysis_data.get("their_actual_new_message"),
        detected_archetype=analysis_data.get("detected_archetype"),
        archetype_reasoning=analysis_data.get("archetype_reasoning"),
    )

    # Parse strategy
    strategy_data = data.get("strategy", {})
    strategy = StrategyResult(
        wrong_moves=strategy_data.get("wrong_moves", []),
        right_energy=strategy_data.get("right_energy", ""),
        hook_point=strategy_data.get("hook_point", ""),
    )

    # Parse replies
    replies = data.get("replies", [])
    if not replies:
        logger.error(
            "parse_json_no_replies",
            data_keys=list(data.keys()),
            raw_data=str(data)[:500],
        )
        raise ValueError("No replies in JSON response")

    # Parse replies into structured ReplyOption objects
    reply_options: list[ReplyOption] = []
    for reply in replies[:4]:
        if isinstance(reply, dict):
            text = str(reply.get("text", "")).strip()
            strategy_label = str(reply.get("strategy_label", "")).strip()
            is_recommended = bool(reply.get("is_recommended", False))
            coach_reasoning = str(reply.get("coach_reasoning", "")).strip()

        else:
            # Defensive fallback: support legacy plain-string replies if Gemini ever ignores schema
            text = str(reply).strip()
            strategy_label = ""
            is_recommended = False
            coach_reasoning = ""

        # Remove numbered prefixes like "1. " or "Reply 1: " from the visible text only
        text = re.sub(r"^(?:\d+[\.\)]\s*|Reply\s*\d+:\s*|[A-Z][a-z]+:\s*)", "", text)

        if not text:
            continue

        reply_options.append(
            ReplyOption(
                text=text,
                strategy_label=strategy_label,
                is_recommended=is_recommended,
                coach_reasoning=coach_reasoning,
            )
        )

    if not reply_options:
        logger.error(
            "parse_json_all_empty",
            replies_raw=str(replies)[:500],
            data_preview=str(data)[:500],
        )
        raise ValueError("All replies were empty after cleaning")

    return ParsedLlmResponse(
        visual_transcript=visual_transcript,
        analysis=analysis,
        strategy=strategy,
        replies=reply_options,
    )
