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
from agent.nodes_v2._shared import (
    AUDITOR_MODEL,
    MAX_REWRITES,
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


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_AUDITOR_SYSTEM_PROMPT = """
Strict quality auditor for AI dating replies. Evaluate 4 replies on substance only. Ignore punctuation/capitalization.

FAIL a reply for ANY of:
* Context/Dialect: Ignores verbatim_last_message. Misses user_custom_hint. Hindi in ENGLISH dialect (or missing Hinglish).
* Archetype: Tone clashes (sincere for BANTER GIRL, shallow for INTELLECTUAL, sarcastic for GUARDED/TESTER, over-eager for LOW-INVESTMENT).
* Direction:
  - get_number: No off-app move, or stiff phrasing ("can i get your number"). NOTE: Direct, confident asks ARE correct for non-GUARDED archetypes — do NOT fail a reply for being "too direct" unless it's actually stiff or pressuring.
  - ask_out: BATCH needs >=2 replies with concrete plan (specific activity + day/time). "take me to your top spot saturday" = PASS. "we should hang sometime" = FAIL. Other 2 may banter. Only fail BATCH if <2 have plans.
  - opener: Generic greeting. Use opener_hook_priority: text_first=anchor bio/story; visual_first=use visual hooks; either=use strongest hook.
  - revive_chat: Stale openers ("hey stranger", "long time").
  - de_escalate: Sarcastic/defensive, OR no acknowledgment before question. NOTE: One warm curious question after acknowledgment is ALLOWED. Only fail if: jumps straight to question with zero acknowledgment, OR question is dismissive/challenging.
* Tone Safety: Teases/escalates when their_tone=upset/vulnerable. Includes: positivity redirect before holding space, implying overreaction, focusing on what she SHOULD do vs what she FEELS. go_deeper: feelings first. de_escalate: acknowledge before redirecting.
* Cringe/Generic: Therapy-speak, motivational quotes, overly eager, copy-paste line.
* Freshness: Identical or close paraphrase of last_ai_replies_shown.
* Forbidden: Dead openers ("hey/hi/so/well"). Empty laugh starts ("haha/lol") unless reacting to specific text. Lazy deflection ("what about you", "tumhe kya lagta hai"). tease direction: echoing her question back verbatim.
* Structure: 2+ questions. Dead-end (no fork/hook). strategy_label mismatch.

GLOBAL BATCH:
* Diversity: 3+ replies same angle → fail weakest.
* Shape: Exactly ONE is_recommended=true. 0 or 2+ → fail weakest.
* Threshold: Good enough to send, not perfect. Don't fail on subjective taste. If 2+ replies fail rules above → fail batch with rewrite instructions.

Return structured JSON.
"""


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


def auditor_node(state: AgentState) -> dict:
    """
    Evaluates the quality of generated replies against context, archetype,
    direction, and substance rules.

    Returns:
      - is_cringe: True if replies need a rewrite
      - auditor_feedback: Specific instructions for the generator on what to fix
    """
    user_id = state.get("user_id", "")
    trace_id = state.get("trace_id", "")
    conversation_id = state.get("conversation_id", "") or ""
    revision_count = state.get("revision_count", 0)
    t_start = time.monotonic()
    logger.info(
        "llm_lifecycle",
        stage="auditor_node_start",
        trace_id=trace_id,
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
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        logger.info(
            "llm_lifecycle",
            stage="auditor_node_complete",
            trace_id=trace_id,
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

    # Safety valve: if we've already rewritten max times, approve regardless
    if revision_count > MAX_REWRITES:
        logger.info(
            "llm_lifecycle",
            stage="auditor_node_complete",
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            skipped=True,
            reason="max_rewrites_skip_audit",
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
        )
        return {"is_cringe": False, "auditor_feedback": ""}

    direction = state.get("direction", "quick_reply")
    custom_hint = (state.get("custom_hint") or "").strip()

    verbatim_last_message = transcript_text_from_analysis(analysis)
    their_last_message_paraphrase = getattr(analysis, "their_last_message", "") or ""

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
        "key_detail": getattr(analysis, "key_detail", ""),
        "direction": direction,
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

    # Pass previously shown replies so the auditor can enforce freshness
    conversation_context = state.get("conversation_context_dict") or {}
    last_ai_replies_shown = (conversation_context.get("last_ai_replies_shown") or [])
    if last_ai_replies_shown:
        eval_payload["last_ai_replies_shown"] = last_ai_replies_shown
    logger.info(
        "llm_lifecycle",
        stage="auditor_node_pre_llm",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        model=AUDITOR_MODEL,
        reply_count=len(eval_payload["replies"]),
        verbatim_last_message_chars=len(verbatim_last_message or ""),
        has_custom_hint=bool(custom_hint),
    )

    messages = [
        SystemMessage(content=_AUDITOR_SYSTEM_PROMPT),
        HumanMessage(content=json.dumps(eval_payload)),
    ]

    logger.info(
        "auditor_node_llm_messages",
        trace_id=trace_id,
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
            trace_id=trace_id,
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
            trace_id=trace_id,
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
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            skipped=True,
            reason="llm_error_approved",
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
        )
        return {"is_cringe": False, "auditor_feedback": ""}

    failed_verdicts = [v for v in audit.verdicts if not v.passes]

    if audit.overall_passes:
        logger.info(
            "auditor_node_full_verdicts",
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            direction=direction,
            overall_passes=True,
            summary=audit.summary,
            verdicts=[
                {
                    "reply_index": v.reply_index,
                    "passes": v.passes,
                    "issue": v.issue,
                }
                for v in audit.verdicts[:4]
            ],
        )
        logger.info(
            "llm_lifecycle",
            stage="auditor_node_complete",
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            overall_passes=True,
            failed_reply_count=len(failed_verdicts),
            elapsed_ms=int((time.monotonic() - t_start) * 1000),
            usage_phase=usage_row.get("phase"),
            usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
            usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
        )
        return {
            "is_cringe": False,
            "auditor_feedback": "",
            "gemini_usage_log": [usage_row],
        }

    # Build structured feedback for the generator
    feedback_lines = [audit.summary, ""]
    for v in failed_verdicts:
        feedback_lines.append(f"- Reply {v.reply_index}: {v.issue}")

    logger.info(
        "auditor_node_full_verdicts",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        overall_passes=False,
        summary=audit.summary,
        verdicts=[
            {
                "reply_index": v.reply_index,
                "passes": v.passes,
                "issue": v.issue,
            }
            for v in audit.verdicts[:4]
        ],
    )

    logger.info(
        "llm_lifecycle",
        stage="auditor_node_complete",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        overall_passes=False,
        failed_reply_count=len(failed_verdicts),
        summary_preview=(audit.summary or "")[:160],
        elapsed_ms=int((time.monotonic() - t_start) * 1000),
        usage_phase=usage_row.get("phase"),
        usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
        usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
    )

    return {
        "is_cringe": True,
        "auditor_feedback": "\n".join(feedback_lines),
        "gemini_usage_log": [usage_row],
    }
