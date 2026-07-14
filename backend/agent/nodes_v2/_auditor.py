"""
Node 3: auditor_node — quality evaluator

Evaluates reply quality against context, archetype, direction, and substance.
Does NOT check style/punctuation (handled by deterministic post-processor).
Returns per-reply verdicts with specific rewrite instructions.
If any reply fails → routes back to generator with feedback (max 1 rewrite).

Model: `settings.gemini_model` (GEMINI_MODEL) at temperature 0 (deterministic judgment)
"""

import json
import time
from typing import cast

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agent.nodes_v2._lc_usage import invoke_structured_gemini
from app.prompts.auditor import _AUDITOR_SYSTEM_PROMPT
from app.prompts.prompt_fragments import (
    BANNED_EXAMPLE_PHRASES,
    SCAFFOLD_RULE,
    STRATEGY_LABEL_GLOSSARY,
    _resolve_scene_direction,
)
from agent.nodes_v2._shared import (
    AUDITOR_MODEL,
    opener_hook_priority,
    transcript_text_from_analysis,
    sanitize_llm_messages_for_logging,
)
from agent.state import AgentState, AnalystOutput, WriterOutput

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class ReplyVerdict(BaseModel):
    """Per-reply evaluation verdict."""

    reply_index: int = Field(description="0-based index of the reply being evaluated.")
    passes: bool = Field(description="true if this reply is good enough to ship.")
    issue: str = Field(
        default="",
        description=(
            "If passes=false, a specific 1-sentence description of what's wrong. "
            "Be precise: 'Reply 2 uses sarcasm for a WARM/STEADY archetype' "
            "not 'Reply 2 is bad'."
        ),
    )
    pivot_suggestion: str = Field(
        default="",
        description=(
            "If passes=false, suggest a SPECIFIC new angle or hook the writer should pivot to instead. "
            "Name an exact unused detail from the payload (key_detail, visual_hooks, verbatim_last_message, "
            "photo_persona, inbound_image_detail, etc.) and the move/energy to use with it. "
            "Example: 'Pivot completely away from singing/stress and anchor instead on her photo_persona "
            "(soft romantic) — write a line about the black and white saree photo.' "
            "Must be concrete and actionable — never generic like 'be more creative'."
        ),
    )


class AuditorNodeOutput(BaseModel):
    """Structured auditor evaluation of all 4 replies."""

    overall_passes: bool = Field(
        description="true if ALL replies are good enough to ship without rewrite."
    )
    verdicts: list[ReplyVerdict] = Field(
        description="One verdict per reply. Must have exactly 4 entries."
    )
    summary: str = Field(
        description=(
            "If overall_passes=false, a 2-3 sentence summary of the main issues "
            "and what the generator should fix on rewrite. If overall_passes=true, "
            "write 'All replies pass quality check.'"
        ),
    )


# The auditor system prompt is imported from app/prompts/auditor.py at the top of this file.


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


async def auditor_node(state: AgentState) -> dict:
    """
    Evaluates the quality of generated replies against context, archetype,
    direction, and substance rules.

    Returns:
      - is_cringe: True if replies need a rewrite
      - auditor_feedback: Specific instructions for the generator on what to fix
    """
    user_id = state.get("user_id", "")
    conversation_id = state.get("conversation_id", "") or ""
    revision_count = state.get("revision_count", 0)
    t_start = time.monotonic()
    logger.info(
        "llm_lifecycle",
        stage="auditor_node_start",
        user_id=user_id,
        conversation_id=conversation_id,
        direction=state.get("direction", "quick_reply"),
        revision_count=revision_count,
    )

    analysis = state.get("analysis")
    if isinstance(analysis, dict):
        analysis = AnalystOutput(**analysis)
    elif isinstance(analysis, str):
        analysis = AnalystOutput(**json.loads(analysis))

    drafts = state.get("drafts")
    if drafts is None:
        logger.warning(
            "auditor_node_no_drafts",
                user_id=user_id,
            conversation_id=conversation_id,
        )
        logger.info(
            "llm_lifecycle",
            stage="auditor_node_complete",
                user_id=user_id,
            conversation_id=conversation_id,
            skipped=True,
            reason="no_drafts",
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
        )
        return {"is_cringe": False, "auditor_feedback": ""}

    if isinstance(drafts, dict):
        drafts = WriterOutput(**drafts)
    elif isinstance(drafts, str):
        drafts = WriterOutput(**json.loads(drafts))

    # NOTE: we used to skip the audit entirely after the max rewrite and force a
    # pass — that shipped the rewrite UN-audited and made telemetry lie. Now we
    # always audit (the graph caps rewrites at revision_count >= 2, so this just
    # produces an HONEST final verdict; if it still fails we ship anyway, but the
    # real is_cringe + feedback are recorded for analysis).

    direction = state.get("direction", "quick_reply")
    custom_hint = (state.get("custom_hint") or "").strip()
    conversation_context = state.get("conversation_context_dict") or {}

    verbatim_last_message = transcript_text_from_analysis(analysis)
    their_last_message_paraphrase = getattr(analysis, "their_last_message", "") or ""

    # --- Enrich auditor context so the showrunner has the same brief as the writer ---

    # Resolve person_name from analysis or conversation context (same logic as generator)
    person_name = getattr(analysis, "person_name", None) or "unknown"
    convo_ctx_person = (conversation_context or {}).get("person_name")
    if convo_ctx_person and str(convo_ctx_person).lower() != "unknown":
        person_name = str(convo_ctx_person)

    # Transform raw direction into screenplay scene description (same as generator)
    scene_direction = _resolve_scene_direction(direction)

    # Pull the generator's strategy output so the showrunner sees the writer's intent
    gen_strategy = state.get("strategy")
    generator_strategy = {}
    if gen_strategy:
        if isinstance(gen_strategy, dict):
            generator_strategy = gen_strategy
        elif hasattr(gen_strategy, "model_dump"):
            generator_strategy = gen_strategy.model_dump()

    # Build a concise evaluation payload (don't send the whole kitchen sink)
    eval_payload: dict = {
        "detected_archetype": getattr(analysis, "detected_archetype", ""),
        "detected_dialect": getattr(analysis, "detected_dialect", "ENGLISH"),
        "their_tone": getattr(analysis, "their_tone", ""),
        "their_effort": getattr(analysis, "their_effort", ""),
        "conversation_temperature": getattr(analysis, "conversation_temperature", ""),
        "stage": getattr(analysis, "stage", ""),
        "verbatim_last_message": verbatim_last_message,
        "their_last_message_paraphrase": their_last_message_paraphrase,
        "user_last_move": getattr(analysis, "user_last_move", ""),
        "inbound_image": getattr(analysis, "inbound_image", "none"),
        "inbound_image_detail": getattr(analysis, "inbound_image_detail", "") or "",
        "key_detail": getattr(analysis, "key_detail", ""),
        "photo_persona": getattr(analysis, "photo_persona", "") or "",
        "direction": direction,
        "scene_direction": scene_direction,
        "person_name": person_name,
        "generator_strategy": generator_strategy,
        "user_custom_hint": custom_hint,
        "replies": [
            {
                "index": i,
                "text": r.text,
                "strategy_label": r.strategy_label,
                "is_recommended": r.is_recommended,
                "coach_reasoning": r.coach_reasoning,
            }
            for i, r in enumerate(drafts.replies[:4])
        ],
    }
    if direction == "opener":
        eval_payload["visual_hooks"] = getattr(analysis, "visual_hooks", None) or []
        eval_payload["opener_hook_priority"] = opener_hook_priority(
            analysis, verbatim_last_message
        )

    # NOTE: last_ai_replies_shown is no longer sent to the auditor — stale line
    # prevention is now the generator's responsibility via its system prompt.
    logger.info(
        "llm_lifecycle",
        stage="auditor_node_pre_llm",
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        model=AUDITOR_MODEL,
        reply_count=len(eval_payload["replies"]),
        verbatim_last_message_chars=len(verbatim_last_message or ""),
        has_custom_hint=bool(custom_hint),
    )

    messages = [
        SystemMessage(
            content=_AUDITOR_SYSTEM_PROMPT.replace("%SCAFFOLD_RULE%", SCAFFOLD_RULE)
            + "\n\n"
            + STRATEGY_LABEL_GLOSSARY
            + "\n\n"
            + BANNED_EXAMPLE_PHRASES
        ),
        HumanMessage(content=json.dumps(eval_payload)),
    ]

    logger.info(
        "auditor_node_llm_messages",
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        phase="v2_auditor",
        model=AUDITOR_MODEL,
        messages=sanitize_llm_messages_for_logging(messages),
    )

    try:
        result, usage_row = invoke_structured_gemini(
            model=AUDITOR_MODEL,
            temperature=0,
            schema=AuditorNodeOutput,
            messages=messages,
            phase="v2_auditor",
        )
        audit = cast(AuditorNodeOutput, result)
        logger.info(
            "auditor_node_llm_result",
                user_id=user_id,
            conversation_id=conversation_id,
            direction=direction,
            phase="v2_auditor",
            out=audit.model_dump(),
            usage_phase=usage_row.get("phase"),
            usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
            usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
        )
    except Exception as e:
        # Auditor failure should never block the response — approve and ship
        logger.error(
            "auditor_node_llm_error",
                user_id=user_id,
            conversation_id=conversation_id,
            direction=direction,
            error=str(e),
            error_type=type(e).__name__,
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
        )
        logger.info(
            "llm_lifecycle",
            stage="auditor_node_complete",
                user_id=user_id,
            conversation_id=conversation_id,
            skipped=True,
            reason="llm_error_approved",
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
        )
        return {"is_cringe": False, "auditor_feedback": ""}
    failed_verdicts = [v for v in audit.verdicts if not v.passes]

    # ---------------------------------------------------------------------------
    # Targeted Rewrite Mapping (Extract Winners vs Losers)
    # ---------------------------------------------------------------------------
    passed_replies = []
    failed_assignments = []
    feedback_lines = [audit.summary, ""]

    for idx, verdict in enumerate(audit.verdicts[:4]):
        original_reply = eval_payload["replies"][idx]

        if verdict.passes:
            passed_replies.append(original_reply)
            feedback_lines.append(
                f"- Reply {idx}: PASS — keep this structure and hook exactly, only improve the failing replies."
            )
        else:
            failed_assignments.append(
                {
                    "slot_index": idx,
                    "assigned_hook": original_reply["text"],
                    "strategy_label": original_reply["strategy_label"],
                    "pivot_suggestion": verdict.pivot_suggestion or verdict.issue,
                }
            )
            line = f"- Reply {idx}: {verdict.issue}"
            if verdict.pivot_suggestion:
                line += f"\n  PIVOT → {verdict.pivot_suggestion}"
            feedback_lines.append(line)

    logger.info(
        "auditor_node_full_verdicts",
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        overall_passes=audit.overall_passes,
        summary=audit.summary,
        passed_count=len(passed_replies),
        failed_count=len(failed_assignments),
    )

    logger.info(
        "llm_lifecycle",
        stage="auditor_node_complete",
        user_id=user_id,
        conversation_id=conversation_id,
        overall_passes=audit.overall_passes,
        failed_reply_count=len(failed_assignments),
        summary_preview=(audit.summary or "")[:160],
        elapsed_ms=int((time.monotonic() - t_start) * 1000),
        usage_phase=usage_row.get("phase"),
        usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
        usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
    )

    return {
        "is_cringe": not audit.overall_passes,
        "safe_replies": passed_replies,
        "failed_assignments": failed_assignments,
        "auditor_feedback": "\n".join(feedback_lines),
        "gemini_usage_log": [usage_row],
    }
