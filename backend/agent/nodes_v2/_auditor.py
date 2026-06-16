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
    BANNED_EXAMPLE_PHRASES,
    SCAFFOLD_RULE,
    STRATEGY_LABEL_GLOSSARY,
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
* Tone fit + safety (state-based, NOT a label): fail only REAL clashes — heavy teasing/sarcasm toward someone guarded/vulnerable/upset; over-eager chasing toward a cold/low-effort person; CRUDE/vulgar or religion/caste/region jokes toward a traditional/reserved person. A confident cocky TEASE toward a traditional/sincere woman is FINE and wanted — never fail it for being bold; only crude or values-mocking. When her tone is upset/vulnerable: feelings first (go_deeper), acknowledge before any redirect (de_escalate); fail positivity-redirect-before-holding-space or implying she's overreacting. Never fail a reply just for differing from an archetype label.
* Direction:
  - get_number: No off-app move, or stiff phrasing ("can i get your number"). NOTE: Direct, confident asks ARE correct for non-GUARDED archetypes — do NOT fail a reply for being "too direct" unless it's actually stiff or pressuring.
  - ask_out: BATCH needs >=2 replies with a concrete off-app ask anchored to THIS conversation (activity + timing). "take me to your top spot saturday" = PASS. "we should hang sometime" = FAIL (generic, no anchor). Day specificity depends on warmth: warm/hot → specific day required; lukewarm/cold → "this week" or "you pick the day" counts as concrete (do NOT fail a lukewarm-appropriate open-ended ask for lacking a specific day). A logistics question ("are you based in delhi?") counts as one plan slot when city is unknown. Other 2 replies may banter. Only fail BATCH if <2 have concrete asks.
  - opener: Generic greeting. Use opener_hook_priority: text_first=anchor bio/story; visual_first=use visual hooks; either=use strongest hook.
  - revive_chat: Stale openers ("hey stranger", "long time").
  - de_escalate: Sarcastic/defensive, OR no acknowledgment before question. NOTE: One warm curious question after acknowledgment is ALLOWED. Only fail if: jumps straight to question with zero acknowledgment, OR question is dismissive/challenging.* Misattributed blame: If user_last_move says the USER's own last reply was the weak link (low-effort) and her tone cooled in response, FAIL any reply that mocks/accuses HER (calls her share fake, a "showpiece", dismissive, boring, etc.) — it blames her for the user's weak move. Keep the chosen direction, but the tease/move must target the situation or the awkward beat, not her sincerity.
* Persona labeling (litmus = DOES vs IS): fail ONLY a verdict on WHO SHE IS, never a guess about what she DOES. ALLOW behavior/habit assumptions even in "type who" form ("type who treats dates like a job interview", "bet you take 500 photos to get one") → PASS. FAIL only an identity/character/aesthetic/zodiac VERDICT ("influencer energy", "you're the artsy type", "scorpio so you think everyone's wrong"). When unsure, PASS.
* Inbound image: if inbound_image="object_or_scene", FAIL any reply that compliments her looks/appearance (she shared an object/moment, NOT herself). If inbound_image="selfie_of_her", FAIL replies that ignore the image entirely (act as if it's plain text) OR describe her clinically/creepily.
* Cringe/Generic: motivational quotes, overly eager, copy-paste lines. Fate/destiny openers ("us matching was fate / meant to be / the universe's doing") = automatic fail — the most overused opener on every app.
* Therapy/validation phrases (zero tolerance — scan EVERY reply): "i appreciate", "i appreciate the honesty", "i admire", "i hear you", "i hear that", "i respect that", "i really value", "i love that", "that sounds hard", "i understand where youre coming from", "thank you for sharing". PATTERN: any "i [appreciate/admire/respect/love/value/honor] [the/your] ___" first-person validation of her trait/choice fails too, even if the exact verb isn't listed. These read as AI-validation and must fail regardless of direction (the de_escalate/go_deeper acknowledgment uses raw short empathy like "that sounds brutal", NOT these phrases).
* Freshness: Identical or close paraphrase of last_ai_replies_shown.
* Recycled examples: FAIL any reply that reuses a BANNED EXAMPLE LINE from the list below (e.g. "snooze 6 times", "rot on the couch", "taste in music", "biryani excuse", "goa as their answer") — these are prompt illustrations, not content to send. Exception: a detail that is genuinely on her profile.
* Forbidden: Dead openers ("hey/hi/so/well"). Empty laugh starts ("haha/lol") unless reacting to specific text. Lazy deflection ("what about you", "tumhe kya lagta hai"). tease direction: echoing her question back verbatim.
* Structure: 2+ questions. Dead-end (no fork/hook).
* Label accuracy: each reply's strategy_label MUST match its text per the STRATEGY LABEL DEFINITIONS below. FAIL a reply whose label is wrong — e.g. a "would you rather / A or B" question labeled HONEST FRAME (it's FRAME CONTROL); a line that only validates labeled as a tactic (it's HONEST FRAME). In the issue, name the correct label so the generator can fix it.
* Flatness / no-spike (THE RIZZ BAR — applies to EVERY direction EXCEPT de_escalate/go_deeper, and is SUSPENDED when her tone is upset/vulnerable): FAIL a reply that is "safe but boring" — a pure observation ("the cafe looks nice"), a neutral interview question ("whats your favorite X", a flat "a or b" with no assumption/edge baked in), validation ("makes sense you want long-term"), or small talk. A sendable reply needs a SPIKE: a bold playful assumption, a light challenge/disqualification, a cocky-confident frame, or a real stance. "Breaks no rules but any nice guy could send it" = FAIL. (Do NOT demand a spike for de_escalate/go_deeper or an upset/vulnerable tone — warmth wins there.)
* NON-ANCHORED / GENERIC CRUTCH (any direction): FAIL a reply built on an imported generic trope instead of HER words — a hypothetical like "zombie apocalypse / desert island / if you won the lottery / teleportation / stranded on an island / two truths and a lie", or a lazy zodiac-personality read. LITMUS: strip her specifics — if the line still works on ANY match, it's generic → fail. This is a STRUCTURAL anchoring fail, not phrasing taste: a sendable reply hooks her verbatim words/photos, not a clever trope that ignores the conversation. (Exception: de_escalate/go_deeper warmth lines need no hook.)
* AI-SMELL — SCAFFOLD OPENERS (qualitative; do NOT judge length here — an exact word counter enforces the length cap separately, so NEVER fail a reply for being "too long" and NEVER estimate a word count): FAIL a reply ONLY if (a) it opens with a scaffold per this rule — %SCAFFOLD_RULE% — or (b) it lands its spike then trails a SEPARATE explaining clause instead of stopping. The reply must STILL anchor to her specifics (non-anchored rule above). When unsure whether something is a scaffold vs an allowed behavior jab, PASS it.

GLOBAL BATCH:
* Diversity: each reply must anchor a DIFFERENT specific detail. FAIL the weaker of ANY PAIR that hits the SAME SPECIFIC hook with the SAME move (two "tell me more about X" on one detail), and FAIL the batch if 3+ replies re-hit ONE specific hook (e.g. all four about her "long-term" goal). BUT four DIFFERENT specific details count as diverse even if several are visual — her jewelry vs her setting vs a specific dress vs her style range is GOOD spread, NOT a violation (do not fail it for being "all about her style"). On sparse photo-only profiles, distinct visual details ARE the correct diversity. Referencing a specific style/outfit CHOICE is allowed; only generic body/face compliments are banned.
* Shape: Exactly ONE is_recommended=true. 0 or 2+ → fail weakest.
* Threshold: "good enough to send" = has a SPIKE and no clear violation. Do NOT nitpick HOW a spike is phrased ("borders on / feels slightly / a bit too / too X for the archetype" = subjective taste → PASS). Fail only (a) an unambiguous rule violation (banned phrase, identity label, generic greeting, scaffold opener, non-anchored generic crutch, 3+ on one hook) or (b) flatness (no spike at all). Don't fail bold-but-imperfect; DO fail safe-but-boring. Length is the word counter's job — never yours.

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

    # NOTE: we used to skip the audit entirely after the max rewrite and force a
    # pass — that shipped the rewrite UN-audited and made telemetry lie. Now we
    # always audit (the graph caps rewrites at revision_count >= 2, so this just
    # produces an HONEST final verdict; if it still fails we ship anyway, but the
    # real is_cringe + feedback are recorded for analysis).

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
        "user_last_move": getattr(analysis, "user_last_move", ""),
        "inbound_image": getattr(analysis, "inbound_image", "none"),
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

    # Deterministic length backstop. LLMs can't reliably count words, so the
    # prompt-level "TOO LONG / AI-SMELL" rule under-fires (a 21-word reply slipped
    # past it in prod, and its rewrite stayed 21 words because length never reached
    # the feedback). Enforce a hard ceiling here so essay-length replies always get
    # flagged and fed back on rewrite. Set above the soft ~12 target and Hinglish-
    # aware (particles like yaar/matlab/toh inflate the count) so punchy lines pass.
    _LENGTH_HARD_CAP = 18
    by_index = {v.reply_index: v for v in audit.verdicts}
    for i, r in enumerate(drafts.replies[:4]):
        wc = len((getattr(r, "text", "") or "").split())
        if wc <= _LENGTH_HARD_CAP:
            continue
        issue = (
            f"Reply {i} is {wc} words — too long, reads as written not texted. "
            "Cut to <=12: fire the spike and stop, drop the explaining clause."
        )
        existing = by_index.get(i)
        if existing is None:
            audit.verdicts.append(ReplyVerdict(reply_index=i, passes=False, issue=issue))
        elif existing.passes:
            # Only override a PASS; keep an existing fail's (often more specific) issue.
            existing.passes = False
            existing.issue = issue
    if any(not v.passes for v in audit.verdicts):
        audit.overall_passes = False

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
