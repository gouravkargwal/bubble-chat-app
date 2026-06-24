"""
Node 2: generator_node

Single Gemini call with structured output that performs:
  1. Strategy decision (wrong moves, right energy, hook point, label)
  2. Write 4 reply options
  3. On rewrites: incorporates auditor feedback to fix flagged replies

Model: `settings.gemini_model` (GEMINI_MODEL) with dynamic temperature
"""

import json
import time
from typing import Any, cast

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agent.nodes_v2._lc_usage import invoke_structured_gemini, invoke_structured_groq
from agent.nodes_v2._post_processor import validate_and_fix_replies
from agent.nodes_v2._shared import (
    GENERATOR_MODEL,
    opener_hook_priority,
    transcript_text_from_analysis,
    sanitize_llm_messages_for_logging,
)
from agent.state import (
    AgentState,
    AnalystOutput,
    ReplyOption,
    StrategyLabel,
    StrategyOutput,
    WriterOutput,
)
from app.config import settings
from app.prompts.generator import _build_generator_prompt
from app.prompts.temperature import calculate_temperature

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class GeneratorOutput(BaseModel):
    """Combined strategy + writer output from a single call with structured output."""

    # Strategy thinking
    wrong_moves: list[str] = Field(
        description="2-3 concrete anti-patterns or vibes to avoid for this exact context."
    )
    right_energy: str = Field(
        description="Single phrase naming the tone/energy the set of replies should embody."
    )
    hook_point: str = Field(
        description="The main specific detail, tension, or thread to build around (named explicitly)."
    )
    recommended_strategy_label: StrategyLabel = Field(
        description=(
            "The headline strategy for the recommended reply. "
            "If double-texting, favor PATTERN INTERRUPT or VALUE ANCHOR to re-engage."
        )
    )

    # Writer output — exactly 4 reply options
    replies: list[ReplyOption] = Field(
        description=(
            "Exactly 4 reply options. Exactly ONE must have is_recommended=true. "
            "Four genuinely different angles — no repeated hook or parallel phrasing."
        )
    )


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


def generator_node(state: AgentState) -> dict:
    """
    Gemini call with structured output that performs:
      1. Strategy decision (wrong moves, right energy, hook point, label)
      2. Write 4 reply options
      3. On rewrites: incorporates auditor feedback to fix flagged replies

    Uses dynamic temperature from direction × conversation state.
    Returns partial state update (LangGraph merges into full state).
    """
    user_id = state.get("user_id", "")
    trace_id = state.get("trace_id", "")
    conversation_id = state.get("conversation_id", "") or ""
    revision_count = state.get("revision_count", 0)
    auditor_feedback = state.get("auditor_feedback", "")
    is_rewrite = revision_count > 0 and bool(auditor_feedback)

    analysis = state.get("analysis")
    if analysis is None:
        raise ValueError("generator_node requires 'analysis' in state.")
    # LangGraph may serialize Pydantic models to dict or str when passing state
    if isinstance(analysis, dict):
        analysis = AnalystOutput(**analysis)
    elif isinstance(analysis, str):
        analysis = AnalystOutput(**json.loads(analysis))

    direction = state.get("direction", "quick_reply")
    custom_hint = (state.get("custom_hint") or "").strip()
    voice_dna = state.get("voice_dna_dict", {})
    conversation_context = state.get("conversation_context_dict", {})
    core_lore = state.get("core_lore", "") or ""
    past_memories = state.get("past_memories", "") or ""

    # Resolve person_name from context or analysis
    person_name = getattr(analysis, "person_name", None) or "unknown"
    convo_ctx_person = (conversation_context or {}).get("person_name")
    if convo_ctx_person and str(convo_ctx_person).lower() != "unknown":
        person_name = str(convo_ctx_person)

    transcript_text = transcript_text_from_analysis(analysis)

    # --- Dynamic temperature from the matrix ---
    conversation_temperature = (
        getattr(analysis, "conversation_temperature", "warm") or "warm"
    )
    stage = getattr(analysis, "stage", "early_talking") or "early_talking"
    interaction_count = (conversation_context or {}).get("interaction_count", 0)
    llm_temperature = calculate_temperature(
        direction=direction,
        conversation_temperature=conversation_temperature,
        stage=stage,
        interaction_count=(
            interaction_count if isinstance(interaction_count, int) else 0
        ),
        custom_hint=custom_hint,
    )

    # --- Model collapse guard: bump temperature on rewrites to break stale phrasing ---
    # At the base temperature (0.65–0.85) the model stays too close to its original
    # ideas and just shuffles them. A rewrite must force genuinely different angles,
    # so we floor the temp to 0.90 so even low-base directions (de_escalate, get_number)
    # get enough randomness, capped at 0.95 to avoid incoherence.
    if is_rewrite:
        llm_temperature = max(llm_temperature + 0.15, 0.90)
        llm_temperature = min(llm_temperature, 0.95)

    detected_archetype = (
        getattr(analysis, "detected_archetype", "THE LOW-INVESTMENT")
        or "THE LOW-INVESTMENT"
    )

    # Phase 4: once enough scans agree, trust the stable archetype over a single
    # noisy per-scan classification. The volatile scan can flip on a short reply;
    # the accumulated mode is far steadier. Only override at >=0.6 confidence.
    stable_archetype = (conversation_context or {}).get("stable_archetype")
    archetype_confidence = (conversation_context or {}).get("archetype_confidence", 0.0)
    try:
        archetype_confidence = float(archetype_confidence)
    except (TypeError, ValueError):
        archetype_confidence = 0.0
    if (
        stable_archetype
        and archetype_confidence >= 0.6
        and str(stable_archetype).strip().upper()
        != str(detected_archetype).strip().upper()
    ):
        logger.info(
            "archetype_stabilized_override",
            scan_archetype=detected_archetype,
            stable_archetype=stable_archetype,
            confidence=archetype_confidence,
        )
        detected_archetype = str(stable_archetype)

    payload: dict[str, Any] = {
        "analysis": analysis.model_dump(),
        "direction": direction,
        "person_name": person_name,
        "core_lore": core_lore,
        "past_memories": past_memories,
        "transcript_text": transcript_text,
        "voice_dna_dict": voice_dna,
        "conversation_context_dict": conversation_context,
        "user_custom_hint": custom_hint,
    }
    # Carry-forward: if THIS scan has no photo read (chat turn, no photos), use the
    # sticky persona captured at the opener so tone stays matched to her vibe.
    if not (payload["analysis"].get("photo_persona") or "").strip():
        carried = (conversation_context or {}).get("photo_persona") or ""
        if carried:
            payload["analysis"]["photo_persona"] = carried
    if direction == "opener":
        payload["opener_hook_priority"] = opener_hook_priority(
            analysis, transcript_text
        )

    # --- On rewrite: inject the previous drafts + auditor feedback ---
    if is_rewrite:
        prev_drafts = state.get("drafts")
        if prev_drafts:
            if isinstance(prev_drafts, dict):
                payload["previous_replies"] = prev_drafts
            elif hasattr(prev_drafts, "model_dump"):
                payload["previous_replies"] = prev_drafts.model_dump()
        payload["AUDITOR_FEEDBACK"] = (
            "CRITICAL: Your previous replies were rejected by the quality auditor. "
            "Fix the specific issues below while keeping what worked. "
            "Do NOT just regenerate from scratch — improve the flagged replies. "
            "If the feedback includes a PIVOT direction, you MUST use that new angle "
            "instead of rephrasing the original idea. PIVOT means throw the old hook "
            "away and write about the suggested detail instead.\n\n"
            f"{auditor_feedback}"
        )

    # --- Build conditional prompt using the screenplay hack ---
    detected_dialect = getattr(analysis, "detected_dialect", "ENGLISH") or "ENGLISH"
    photo_persona = getattr(analysis, "photo_persona", "") or ""
    system_prompt = _build_generator_prompt(
        person_name=person_name,
        direction=direction,
        detected_dialect=str(detected_dialect),
        transcript_text=transcript_text,
        custom_hint=custom_hint,
        photo_persona=photo_persona,
    )

    t_call = time.monotonic()
    phase = "v2_generator_rewrite" if is_rewrite else "v2_generator"
    logger.info(
        "llm_lifecycle",
        stage="generator_node_start",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        detected_archetype=detected_archetype,
        llm_temperature=llm_temperature,
        is_rewrite=is_rewrite,
        revision_count=revision_count,
        has_custom_hint=bool(custom_hint),
        transcript_chars=len(transcript_text or ""),
        core_lore_chars=len(core_lore),
        past_memories_chars=len(past_memories),
        context_interaction_count=(
            interaction_count if isinstance(interaction_count, int) else 0
        ),
        has_voice_dna=bool(voice_dna),
    )

    # Provider routing — the generator (writer) can A/B on Groq while vision/auditor
    # stay on Gemini. GENERATOR_PROVIDER:
    #   "gemini" (default) → Gemini drives the pipeline
    #   "groq"             → Groq drives the pipeline
    #   "both"             → Gemini drives the pipeline AND Groq runs in shadow on the
    #                        SAME prompt (first pass only), both logged in v2_generator_ab
    #                        for side-by-side comparison. Shadow never affects the response.
    _provider = settings.generator_provider.strip().lower()
    _use_groq = _provider == "groq"
    _run_shadow = _provider == "both"
    gen_model = settings.groq_model if _use_groq else GENERATOR_MODEL

    logger.info(
        "llm_lifecycle",
        stage="generator_node_pre_llm",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        model=gen_model,
        provider=settings.generator_provider,
        phase=phase,
        payload_keys=sorted(payload.keys()),
        payload_replies_count=(
            len((payload.get("previous_replies") or {}).get("replies", []))
            if isinstance(payload.get("previous_replies"), dict)
            else 0
        ),
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(payload)),
    ]

    logger.info(
        "generator_node_llm_messages",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        phase=phase,
        model=gen_model,
        provider=settings.generator_provider,
        messages=sanitize_llm_messages_for_logging(messages),
    )

    try:
        _invoke = invoke_structured_groq if _use_groq else invoke_structured_gemini
        result, usage_row = _invoke(
            model=gen_model,
            temperature=llm_temperature,
            schema=GeneratorOutput,
            messages=messages,
            phase=phase,
        )
        gen_out = cast(GeneratorOutput, result)

        # A/B shadow: when GENERATOR_PROVIDER=both, also run Groq on the SAME prompt
        # (first pass only) and log both reply sets side by side. Best-effort — a
        # shadow failure must never affect the real (Gemini) response.
        if _run_shadow and not is_rewrite:
            try:
                shadow_result, _ = invoke_structured_groq(
                    model=settings.groq_model,
                    temperature=llm_temperature,
                    schema=GeneratorOutput,
                    messages=messages,
                    phase="v2_generator_shadow_groq",
                )
                shadow_out = cast(GeneratorOutput, shadow_result)
                logger.info(
                    "v2_generator_ab",
                    trace_id=trace_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    direction=direction,
                    primary_provider="gemini",
                    primary_model=gen_model,
                    primary_replies=[
                        {
                            "text": r.text,
                            "strategy_label": r.strategy_label,
                            "is_recommended": r.is_recommended,
                        }
                        for r in gen_out.replies
                    ],
                    shadow_provider="groq",
                    shadow_model=settings.groq_model,
                    shadow_replies=[
                        {
                            "text": r.text,
                            "strategy_label": r.strategy_label,
                            "is_recommended": r.is_recommended,
                        }
                        for r in shadow_out.replies
                    ],
                )
            except Exception:
                logger.warning(
                    "v2_generator_ab_shadow_failed", trace_id=trace_id, exc_info=True
                )

        logger.info(
            "generator_node_llm_result",
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            direction=direction,
            phase=phase,
            out=gen_out.model_dump(),
            usage_phase=usage_row.get("phase"),
            usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
            usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
        )
    except Exception as e:
        logger.error(
            "agent_v2_generator_llm_error",
            trace_id=trace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            direction=direction,
            error=str(e),
            error_type=type(e).__name__,
            elapsed_ms=int((time.monotonic() - t_call) * 1000),
        )
        raise

    # --- Validate reply count and fix if needed ---
    gen_out = validate_and_fix_replies(gen_out)

    # Full observability: log the exact 4 reply options we plan to ship.
    # NOTE: This can create large log entries; intentionally no truncation.

    logger.info(
        "generator_node_full_output",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        phase=phase,
        recommended_strategy_label=gen_out.recommended_strategy_label,
        wrong_moves=gen_out.wrong_moves,
        right_energy=gen_out.right_energy,
        hook_point=gen_out.hook_point,
        replies=[
            {
                "text": r.text,
                "strategy_label": r.strategy_label,
                "is_recommended": r.is_recommended,
                "coach_reasoning": r.coach_reasoning,
            }
            for r in gen_out.replies[:4]
        ],
    )

    logger.info(
        "llm_lifecycle",
        stage="generator_node_complete",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        phase=phase,
        elapsed_ms=int((time.monotonic() - t_call) * 1000),
        recommended_strategy_label=gen_out.recommended_strategy_label,
        reply_count=len(gen_out.replies),
        usage_phase=usage_row.get("phase"),
        usage_prompt_tokens=usage_row.get("prompt_tokens", 0),
        usage_candidates_tokens=usage_row.get("candidates_tokens", 0),
    )

    # Build StrategyOutput and WriterOutput from GeneratorOutput
    strategy = StrategyOutput(
        wrong_moves=gen_out.wrong_moves,
        right_energy=gen_out.right_energy,
        hook_point=gen_out.hook_point,
        recommended_strategy_label=gen_out.recommended_strategy_label,
    )
    drafts = WriterOutput(replies=gen_out.replies)

    return {
        "strategy": strategy,
        "drafts": drafts,
        "revision_count": revision_count + 1,
        # Clear auditor feedback after consuming it
        "auditor_feedback": "",
        "is_cringe": False,
        "gemini_usage_log": [usage_row],
    }
