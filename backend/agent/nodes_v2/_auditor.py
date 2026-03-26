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
You are a quality auditor for AI-generated dating reply suggestions.
You receive the conversation analysis and 4 generated replies.
Your job: evaluate whether each reply is good enough to show to the user.

NOTE: Punctuation, capitalization, and formatting are fixed automatically by code
after your review. Do NOT evaluate or fail replies for style/punctuation issues.
Focus ONLY on substantive quality:

1. CONTEXT FIT: Does the reply actually respond to what she said?
   PRIMARY ground truth is verbatim_last_message — the exact text from her latest message
   bubble (same string the generator used). Use their_last_message_paraphrase only as
   secondary context; do not fail a reply for paraphrase wording differences.
   A reply that ignores her message or talks about something unrelated = FAIL.

2. ARCHETYPE MATCH: Does the tone match the detected archetype?
   - BANTER GIRL → cocky, teasing, sparring. NOT sincere/serious.
   - INTELLECTUAL → witty, thoughtful, depth. NOT shallow one-liners.
   - WARM/STEADY → confident but warm, light teasing ok. NOT full cocky or overly serious.
   - GUARDED/TESTER → honest, direct, sincere. NOT evasive, deflecting, or sarcastic.
   - EAGER/DIRECT → decisive, warm, leading. NOT playing games or creating artificial tension.
   - LOW-INVESTMENT → unbothered, high-standard. NOT chasing or over-explaining.
   Wrong energy for the archetype = FAIL.

3. DIRECTION COMPLIANCE: Does the reply fulfill the requested direction?
   - "get_number" → at least one reply must include a move-off-app line
   - "opener" → must reference a visual detail, NOT a generic greeting
   - "ask_out" → must include a concrete plan (place/time/activity)
   - "de_escalate" → must NOT be sarcastic, defensive, or dismissive
   - "tease" → must be playful, not mean or generic
   - If user_custom_hint in the payload is non-empty: EVERY reply must clearly reflect that hint
     (not a generic reply that could apply without it). Missing the hint = FAIL.
   Direction violated = FAIL.

4. CRINGE / GENERIC: Would a real person actually send this?
   - Corporate jargon, therapy speak, motivational quotes = FAIL
   - Overly eager ("I'd love to get to know you more!") = FAIL
   - Generic ("What are you up to?", "How's your day?") = FAIL for most directions

5. DIVERSITY: Are all 4 replies using clearly different angles?
   If 3+ replies feel like variations of the same approach = FAIL the weakest one.

6. DIALECT MATCH: If detected_dialect is HINGLISH, replies must be in Hinglish.
   If ENGLISH, replies must NOT contain Hindi words. Mismatch = FAIL.

BE STRICT BUT FAIR:
- A reply doesn't need to be perfect. It needs to be good enough to send.
- If 2+ replies have substantive issues, fail overall with clear rewrite instructions.
- Do NOT fail replies for punctuation, capitalization, or formatting — code handles that.
- Do NOT fail replies just because you'd write them differently. Fail only for
  objective rule violations listed above.

Return your evaluation as structured output.
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
    eval_payload = {
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
            failed_reply_count=0,
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
