"""Parse structured LLM output into domain objects.

Three-tier fallback:
1. Direct JSON parse
2. Extract JSON from markdown code fences
3. Regex-based delimiter extraction (---/=== format)
"""

import json
import re

import structlog

from app.domain.models import AnalysisResult, ParsedLlmResponse, StrategyResult

logger = structlog.get_logger()


def parse_llm_response(raw: str) -> ParsedLlmResponse:
    """Parse LLM output into structured response. Tries 3 strategies."""
    # Strategy 1: Direct JSON parse
    try:
        return _parse_json(raw)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    # Strategy 2: Extract JSON from markdown code block
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if json_match:
        try:
            return _parse_json(json_match.group(1))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Strategy 3: Find any JSON object in the text
    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        try:
            return _parse_json(brace_match.group(0))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Strategy 4: Delimiter-based fallback (---/=== format from V1)
    try:
        return _parse_delimited(raw)
    except Exception:
        pass

    # Last resort: try to extract any 4 distinct lines as replies
    # NOTE: analysis data will be empty defaults — degrades conversation memory
    # and Voice DNA training. Log as error for monitoring.
    lines = [
        line.strip()
        for line in raw.strip().split("\n")
        if line.strip() and len(line.strip()) > 10
    ]
    if len(lines) >= 4:
        logger.error(
            "parse_fallback_lines_no_analysis",
            line_count=len(lines),
            raw_preview=raw[:300],
        )
        return ParsedLlmResponse(
            analysis=AnalysisResult(),
            strategy=StrategyResult(),
            replies=lines[:4],
        )

    raise ValueError(f"Could not parse LLM response: {raw[:200]}")


def _parse_json(text: str) -> ParsedLlmResponse:
    """Parse a JSON response into structured domain objects."""
    data = json.loads(text)

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

    return ParsedLlmResponse(analysis=analysis, strategy=strategy, replies=cleaned)


def _parse_delimited(raw: str) -> ParsedLlmResponse:
    """Fallback: parse the ---/=== delimiter format."""
    # Split by === to separate replies from context
    main_parts = raw.split("===")
    replies_section = main_parts[0].strip()
    context_section = main_parts[1].strip() if len(main_parts) > 1 else ""

    # Split replies by ---
    reply_parts = [r.strip() for r in replies_section.split("---") if r.strip()]

    # Clean reply labels
    cleaned = []
    for reply in reply_parts[:4]:
        reply = re.sub(r"^(?:\d+[\.\)]\s*|Reply\s*\d+:\s*|[A-Z][a-z]+:\s*)", "", reply)
        if reply:
            cleaned.append(reply)

    if len(cleaned) < 2:
        raise ValueError(f"Only found {len(cleaned)} replies in delimited format")

    # Try to extract person name from context
    person_name = "unknown"
    name_match = re.search(r"Person(?:\s*name)?:\s*([^.\n]+)", context_section)
    if name_match:
        person_name = name_match.group(1).strip()

    # Try to extract stage
    stage = "early_talking"
    stage_match = re.search(r"Stage:\s*([^\n.]+)", context_section)
    if stage_match:
        stage = stage_match.group(1).strip().lower().replace(" ", "_")

    return ParsedLlmResponse(
        analysis=AnalysisResult(person_name=person_name, stage=stage),
        strategy=StrategyResult(),
        replies=cleaned,
    )
