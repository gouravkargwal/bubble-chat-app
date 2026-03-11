"""Parse structured LLM output into domain objects.

This module assumes Gemini's native Structured JSON Outputs are enabled.
We expect the raw model output to be a single valid JSON object that
matches our response schema, and we do not perform markdown or regex
fallback extraction.
"""

import json
import re

import structlog

from app.domain.models import AnalysisResult, ParsedLlmResponse, StrategyResult

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
            and "message_text" in item
        ):
            from app.domain.models import VisualTranscriptItem

            visual_transcript.append(
                VisualTranscriptItem(
                    side=str(item.get("side")),
                    sender=str(item.get("sender")),
                    message_text=str(item.get("message_text")),
                )
            )

    if visual_transcript:
        logger.debug("parse_visual_transcript", items=len(visual_transcript))

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

    logger.debug(
        "parse_json_raw_replies",
        replies_type=type(replies).__name__,
        replies_count=len(replies),
        first_reply_type=type(replies[0]).__name__ if replies else None,
        first_reply_preview=str(replies[0])[:200] if replies else None,
    )

    # Clean up replies - handle both string and dict formats
    cleaned = []
    for idx, reply in enumerate(replies[:4]):
        # Handle dict replies (e.g., {"text": "..."} or {"reply": "..."})
        if isinstance(reply, dict):
            reply_text = (
                reply.get("text") or reply.get("reply") or reply.get("content") or ""
            )
            logger.debug(
                "parse_dict_reply",
                index=idx,
                keys=list(reply.keys()),
                text_preview=reply_text[:100],
            )
            reply = str(reply_text).strip()
        else:
            reply = str(reply).strip()

        # Remove numbered prefixes like "1. " or "Reply 1: "
        reply = re.sub(r"^(?:\d+[\.\)]\s*|Reply\s*\d+:\s*|[A-Z][a-z]+:\s*)", "", reply)
        if reply:
            cleaned.append(reply)

    if not cleaned:
        logger.error(
            "parse_json_all_empty",
            replies_raw=str(replies)[:500],
            data_preview=str(data)[:500],
        )
        raise ValueError("All replies were empty after cleaning")

    logger.info(
        "parse_json_success",
        cleaned_count=len(cleaned),
        reply_lengths=[len(r) for r in cleaned],
    )

    return ParsedLlmResponse(
        visual_transcript=visual_transcript,
        analysis=analysis,
        strategy=strategy,
        replies=cleaned,
    )
