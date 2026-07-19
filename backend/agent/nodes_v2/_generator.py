"""
Node 2: generator_node

Async Fan-Out Ensemble Pattern:
  - Fires concurrent LLM calls, each tasked with writing exactly ONE line
    targeting a specific assigned hook and strategy.
  - On rewrite, selectively re-rolls ONLY the failed slots while preserving
    previously approved replies to prevent data leakage and repetition.
  - Stitches results back into the contract expected by the Auditor node.

Model: `settings.gemini_model` (GEMINI_MODEL) with dynamic temperature
"""

import asyncio
import json
import os
import time
from typing import Any, cast

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agent.nodes_v2._lc_usage import invoke_structured_gemini, invoke_structured_groq
from agent.nodes_v2._post_processor import validate_and_fix_replies
from agent.nodes_v2._context_formatter import format_rag_context, fetch_facts_meta
from agent.nodes_v2._shared import (
    GENERATOR_MODEL,
    opener_hook_priority,
    transcript_text_from_analysis,
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
from app.prompts.generator import _build_single_line_prompt
from app.prompts.temperature import calculate_temperature

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schema for single-line calls
# ---------------------------------------------------------------------------


class SingleLineReply(BaseModel):
    """One reply from a single-line async fan-out call."""

    text: str = Field(description="The single reply line from Kabir.")
    strategy_label: StrategyLabel = Field(
        description="Dominant tactic for this reply; must match what the text actually does."
    )
    coach_reasoning: str = Field(
        description=(
            "One short sentence explaining why this angle fits context and archetype, "
            "addressed directly to the user as coaching advice. Write in second person "
            "('you') — never refer to the sender by any character/persona name."
        )
    )


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


async def generator_node(state: AgentState) -> dict:
    """
    Async Fan-Out Generator — fires concurrent LLM calls, writing
    exactly ONE reply anchored on a specific assigned hook and strategy.

    Selectively target-rewrites only failed allocations if in a rewrite loop.
    Uses dynamic temperature from direction x conversation state.
    Returns partial state update (LangGraph merges into full state).
    """
    user_id = state.get("user_id", "")
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
    tier_1_raw = state.get("tier_1_raw_exchanges", "") or ""
    tier_2_summary = state.get("tier_2_summary", "") or ""

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

    # --- Model collapse guard: bump temperature on rewrites ---
    if is_rewrite:
        llm_temperature = max(llm_temperature + 0.15, 0.90)
        llm_temperature = min(llm_temperature, 0.95)

    detected_archetype = (
        getattr(analysis, "detected_archetype", "THE LOW-INVESTMENT")
        or "THE LOW-INVESTMENT"
    )

    # Phase 4: trust stable archetype when confidence is high
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

    # --- Format RAG context with structured sections ---
    # Set RAG_FORMAT_DISABLED=1 to bypass the formatter (for A/B testing).
    _use_raw = os.environ.get("RAG_FORMAT_DISABLED", "") == "1"
    if _use_raw:
        core_lore_for_llm = core_lore
    else:
        # Try to fetch fact metadata for importance sorting + category grouping.
        facts_meta = None
        if conversation_id and user_id:
            try:
                from app.infrastructure.database.engine import librarian_async_session
                async with librarian_async_session() as _db:
                    facts_meta = await fetch_facts_meta(
                        _db, user_id=user_id, conversation_id=conversation_id
                    )
            except Exception:
                facts_meta = None

        formatted_context = format_rag_context(
            core_lore=core_lore,
            tier_1_raw=tier_1_raw,
            tier_2_summary=tier_2_summary,
            facts_meta=facts_meta,
        )
        core_lore_for_llm = formatted_context if formatted_context else core_lore

    # --- Build payload shared across all micro-calls ---
    # We include last_ai_replies_shown so each micro-call can do stale-line prevention.
    shared_payload: dict[str, Any] = {
        "person_name": person_name,
        "direction": direction,
        "detected_dialect": getattr(analysis, "detected_dialect", "ENGLISH")
        or "ENGLISH",
        "transcript_text": transcript_text,
        "photo_persona": getattr(analysis, "photo_persona", "") or "",
        "core_lore": core_lore_for_llm,
        "tier_1_raw_exchanges": tier_1_raw,
        "tier_2_summary": tier_2_summary,
        "voice_dna_dict": voice_dna,
        "conversation_context_dict": conversation_context,
        "custom_hint": custom_hint,
        "key_detail": getattr(analysis, "key_detail", "") or "",
        "visual_hooks": getattr(analysis, "visual_hooks", None) or [],
        "durable_facts": getattr(analysis, "durable_facts", None) or [],
        "their_last_message": getattr(analysis, "their_last_message", "") or "",
        "inbound_image_detail": getattr(analysis, "inbound_image_detail", "") or "",
        "last_ai_replies_shown": (
            (conversation_context or {}).get("last_ai_replies_shown") or []
        ),
    }
    if is_rewrite:
        prev_drafts = state.get("drafts")
        if prev_drafts:
            if isinstance(prev_drafts, dict):
                shared_payload["previous_replies"] = prev_drafts
            elif hasattr(prev_drafts, "model_dump"):
                shared_payload["previous_replies"] = prev_drafts.model_dump()
        shared_payload["AUDITOR_FEEDBACK"] = (
            "CRITICAL: Your previous replies were rejected by the quality auditor. "
            "Fix the specific issues below while keeping what worked. "
            "Do NOT just regenerate from scratch — improve the flagged replies. "
            "If the feedback includes a PIVOT direction, you MUST use that new angle "
            "instead of rephrasing the original idea. PIVOT means throw the old hook "
            "away and write about the suggested detail instead.\n\n"
            f"{auditor_feedback}"
        )

    # On rewrite, also pass previous strategy if available so the ensemble can
    # preserve the winning hooks/labels where the auditor said PASS.
    gen_strategy = state.get("strategy")
    if gen_strategy and is_rewrite:
        if isinstance(gen_strategy, dict):
            shared_payload["previous_strategy"] = gen_strategy
        elif hasattr(gen_strategy, "model_dump"):
            shared_payload["previous_strategy"] = gen_strategy.model_dump()

    if direction == "opener":
        shared_payload["opener_hook_priority"] = opener_hook_priority(
            analysis, transcript_text
        )

    # -----------------------------------------------------------------------
    # Define the 4 strict assignments (hook + strategy per slot)
    # -----------------------------------------------------------------------
    visual_hooks: list[str] = getattr(analysis, "visual_hooks", None) or []
    key_detail: str = getattr(analysis, "key_detail", "") or ""
    photo_persona_hook = getattr(analysis, "photo_persona", "") or ""
    inbound_image_detail = getattr(analysis, "inbound_image_detail", "") or ""
    their_last_message = getattr(analysis, "their_last_message", "") or ""

    # Fallback helpers
    def _first_visual_or_key(idx: int) -> str:
        if idx < len(visual_hooks) and visual_hooks[idx]:
            return visual_hooks[idx]
        return key_detail or "her profile"

    assignments: list[tuple[str, str]] = []

    if direction == "de_escalate":
        # SCENE: DE-ESCALATION. The auditor already has three special-case
        # rules for this scene (fails "sarcastic/defensive tone or no
        # acknowledgment before a question", exempts it from the spike
        # requirement, exempts it from needing a grounded hook) — all signs
        # this scene needs sincere, non-tactical treatment. But the generator
        # was still defaulting to FRAME CONTROL/PATTERN INTERRUPT/PUSH-PULL/
        # VALUE ANCHOR, every one of which risks tripping that exact fail
        # condition. HONEST FRAME (acknowledge, own it) covers the majority;
        # SOFT CLOSE covers the brief's second half ("opens space forward").
        assignments.append(
            ("acknowledging what happened, plainly, before anything else", "HONEST FRAME")
        )
        assignments.append(
            ("owning the specific thing Kabir got wrong or could have done better", "HONEST FRAME")
        )
        assignments.append(
            ("a genuine, non-defensive read of where she's coming from", "HONEST FRAME")
        )
        assignments.append(
            ("a low-pressure opening back toward the conversation", "SOFT CLOSE")
        )
    elif direction == "go_deeper":
        # SCENE: EMOTIONAL BEAT. All 4 replies belong in the same honest,
        # non-tactical register — HONEST FRAME is the only strategy built for
        # this — so instead of 4 different strategy labels we vary the
        # specific MOVE per the scene's own brief (naming / reaction /
        # question / reframe), rather than defaulting to the playful-banter
        # strategies (FRAME CONTROL, PATTERN INTERRUPT, etc.) that scene is
        # explicitly told never to use here.
        assignments.append(
            ("naming what she just shared, plainly and directly", "HONEST FRAME")
        )
        assignments.append(
            ("a short, raw, human reaction to what she said", "HONEST FRAME")
        )
        assignments.append(
            (
                "a genuine, curious question about her inner experience of it",
                "HONEST FRAME",
            )
        )
        assignments.append(
            (
                "a gentle reframe that meets her where she is, no advice or pep talk",
                "HONEST FRAME",
            )
        )
    elif direction == "revive_chat":
        # SCENE: WARM RE-ENGAGEMENT. FRAME CONTROL ("force her to defend or
        # play along") and PATTERN INTERRUPT ("cuts right through curated
        # pretense") are both written in a confrontational register that
        # directly contradicts this scene's own brief — "NOT the moment for
        # a cocky jab, a harsh tease, or an accusation." SOFT CLOSE (low-
        # pressure, relaxed) replaces them here instead.
        assignments.append((key_detail or "something she shared before", "SOFT CLOSE"))
        assignments.append((_first_visual_or_key(0), "SOFT CLOSE"))
        assignments.append((_first_visual_or_key(1), "PUSH-PULL"))
        assignments.append(
            (
                inbound_image_detail
                or _first_visual_or_key(2)
                or photo_persona_hook
                or their_last_message
                or "any unused detail",
                "VALUE ANCHOR",
            )
        )
    elif direction == "get_number":
        # SCENE: MOVING OFF-APP. Brief requires "at least 3 of 4 replies
        # include an explicit ask anchored to something specific" — none of
        # the playful-banter strategies (nor SOFT CLOSE, which stops short of
        # a hard ask) actually make a concrete ask, so DIRECT ASK covers 3
        # slots here, with one playful slot kept for variety.
        assignments.append((key_detail or "her profile", "DIRECT ASK"))
        assignments.append((_first_visual_or_key(0), "DIRECT ASK"))
        assignments.append((_first_visual_or_key(1), "DIRECT ASK"))
        assignments.append(
            (
                inbound_image_detail
                or _first_visual_or_key(2)
                or photo_persona_hook
                or their_last_message
                or "any unused detail",
                "VALUE ANCHOR",
            )
        )
    elif direction == "ask_out":
        # SCENE: DATE REQUEST. Brief requires "at least 2 of 4 replies
        # include a concrete, conversation-anchored ask with a specific
        # activity" — DIRECT ASK covers 2 slots, the other 2 stay playful so
        # the user has a banter option alongside the direct ones.
        assignments.append((key_detail or "her profile", "DIRECT ASK"))
        assignments.append((_first_visual_or_key(0), "DIRECT ASK"))
        assignments.append((_first_visual_or_key(1), "PUSH-PULL"))
        assignments.append(
            (
                inbound_image_detail
                or _first_visual_or_key(2)
                or photo_persona_hook
                or their_last_message
                or "any unused detail",
                "VALUE ANCHOR",
            )
        )
    elif (
        direction == "opener"
        and opener_hook_priority(analysis, transcript_text) == "text_first"
    ):
        # Text-first opener: Reply 1 anchors on bio/text
        assignments.append(
            (
                key_detail or photo_persona_hook or "her profile",
                "FRAME CONTROL",
            )
        )
        assignments.append((_first_visual_or_key(0), "PATTERN INTERRUPT"))
        assignments.append((_first_visual_or_key(1), "PUSH-PULL"))
        assignments.append(
            (
                inbound_image_detail or _first_visual_or_key(2) or "any bio detail",
                "VALUE ANCHOR",
            )
        )
    else:
        # Default slot mapping
        assignments.append((key_detail or "her profile", "FRAME CONTROL"))
        assignments.append((_first_visual_or_key(0), "PATTERN INTERRUPT"))
        assignments.append((_first_visual_or_key(1), "PUSH-PULL"))
        assignments.append(
            (
                inbound_image_detail
                or _first_visual_or_key(2)
                or photo_persona_hook
                or their_last_message
                or "any unused detail",
                "VALUE ANCHOR",
            )
        )

    # -----------------------------------------------------------------------
    # Provider routing
    # -----------------------------------------------------------------------
    _provider = settings.generator_provider.strip().lower()
    _use_groq = _provider == "groq"
    _run_shadow = _provider == "both"
    gen_model = settings.groq_model if _use_groq else GENERATOR_MODEL

    phase = "v2_generator_rewrite" if is_rewrite else "v2_generator"

    # -----------------------------------------------------------------------
    # Targeted Rewrite Pre-Population Logic (Filter Winners vs Losers)
    # -----------------------------------------------------------------------
    stitched_slots: dict[int, ReplyOption] = {}
    failed_assignments = state.get("failed_assignments", [])

    if is_rewrite:
        # Load up the lines that previously passed so we don't clear them out
        for sr in state.get("safe_replies", []):
            idx = sr.get("index")
            if idx is not None:
                stitched_slots[idx] = ReplyOption(
                    text=sr["text"],
                    strategy_label=sr["strategy_label"],
                    is_recommended=sr.get("is_recommended", False),
                    coach_reasoning=sr.get("coach_reasoning", ""),
                )

    # Establish localized logging configurations for fan-out execution
    active_assignments = []
    if is_rewrite and failed_assignments:
        for fa in failed_assignments:
            idx = fa["slot_index"]
            strategy = fa["strategy_label"]
            hook = assignments[idx][0] if idx < len(assignments) else "her profile"
            active_assignments.append((idx, hook, strategy))
    else:
        active_assignments = [
            (idx, hook, strategy) for idx, (hook, strategy) in enumerate(assignments)
        ]

    logger.info(
        "llm_lifecycle",
        stage="generator_node_start",
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
        tier_1_chars=len(tier_1_raw),
        tier_2_chars=len(tier_2_summary),
        context_interaction_count=(
            interaction_count if isinstance(interaction_count, int) else 0
        ),
        has_voice_dna=bool(voice_dna),
        fan_out_count=len(active_assignments),
        assignments=active_assignments,
    )

    logger.info(
        "generator_node_pre_llm",
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        model=gen_model,
        provider=settings.generator_provider,
        phase=phase,
        payload_keys=sorted(shared_payload.keys()),
    )

    # -----------------------------------------------------------------------
    # Async Fan-Out: build target coroutines and fire concurrently
    # -----------------------------------------------------------------------
    t_call = time.monotonic()

    async def _call_single_line(
        slot_index: int,
        assigned_hook: str,
        assigned_strategy: str,
    ) -> tuple[int, SingleLineReply | None, dict]:
        """Run one single-line LLM call. Returns (index, result, usage_row)."""
        system_prompt = _build_single_line_prompt(
            person_name=person_name,
            direction=direction,
            detected_dialect=shared_payload["detected_dialect"],
            transcript_text=transcript_text,
            assigned_hook=assigned_hook,
            assigned_strategy=assigned_strategy,
            custom_hint=custom_hint,
            photo_persona=shared_payload["photo_persona"],
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(shared_payload)),
        ]

        call_phase = f"{phase}_slot_{slot_index}"

        logger.info(
            "generator_fan_out_slot_start",
                slot=slot_index,
            assigned_hook=assigned_hook,
            assigned_strategy=assigned_strategy,
            phase=call_phase,
            model=gen_model,
        )

        t0 = time.monotonic()
        try:
            result, usage_row = await asyncio.to_thread(
                _invoke_sync,
                model=gen_model,
                temperature=llm_temperature,
                schema=SingleLineReply,
                messages=messages,
                phase=call_phase,
                use_groq=_use_groq,
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "generator_fan_out_slot_complete",
                        slot=slot_index,
                phase=call_phase,
                elapsed_ms=elapsed_ms,
                text=(result.text or "")[:60],
                strategy_label=result.strategy_label,
            )
            return slot_index, result, usage_row
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            logger.error(
                "generator_fan_out_slot_error",
                        slot=slot_index,
                phase=call_phase,
                error=str(exc),
                error_type=type(exc).__name__,
                elapsed_ms=elapsed_ms,
            )
            return slot_index, None, {}

    def _invoke_sync(
        *,
        model: str,
        temperature: float,
        schema: type[BaseModel],
        messages: list,
        phase: str,
        use_groq: bool,
    ) -> tuple[Any, dict]:
        """Sync invoke wrapper for asyncio.to_thread."""
        _invoke = invoke_structured_groq if use_groq else invoke_structured_gemini
        return _invoke(
            model=model,
            temperature=temperature,
            schema=schema,
            messages=messages,
            phase=phase,
        )

    # Fire ONLY the required micro-calls concurrently
    tasks = [
        _call_single_line(idx, hook, strategy)
        for idx, hook, strategy in active_assignments
    ]
    raw_results = asyncio.gather(*tasks, return_exceptions=True)
    results = await raw_results

    # -----------------------------------------------------------------------
    # Stitch: build reply list preserving slot order
    # -----------------------------------------------------------------------
    replies: list[ReplyOption] = []
    usage_rows: list[dict] = []
    recommended_strategy: str = assignments[0][1]  # default fallback
    first_success = len(stitched_slots) > 0

    sorted_items: list[tuple[int, Any]] = []
    for r in results:
        if isinstance(r, Exception):
            logger.error(
                "generator_fan_out_exception",
                        error=str(r),
                error_type=type(r).__name__,
            )
            continue
        sorted_items.append(r)
    sorted_items.sort(key=lambda x: x[0])

    for slot_index, single_line_result, usage_row in sorted_items:
        if usage_row:
            usage_rows.append(usage_row)

        if single_line_result is None:
            # Slot failed — inject localized fallback so we still return complete array
            fallback_label = (
                assignments[slot_index][1]
                if slot_index < len(assignments)
                else "PATTERN INTERRUPT"
            )
            fallback_text = f"(slot {slot_index + 1} failed — generated fallback)"
            stitched_slots[slot_index] = ReplyOption(
                text=fallback_text,
                strategy_label=fallback_label,
                is_recommended=False,
                coach_reasoning="(auto-generated fallback due to slot failure)",
            )
            continue

        # Determine is_recommended locally for newly generated lines if no slots exist
        is_rec = not first_success
        if is_rec:
            first_success = True

        stitched_slots[slot_index] = ReplyOption(
            text=single_line_result.text,
            strategy_label=single_line_result.strategy_label,
            is_recommended=is_rec,
            coach_reasoning=single_line_result.coach_reasoning,
        )

    # Flatten the finalized stitched map back to standard list ordering (Slots 0-3)
    for i in range(4):
        if i in stitched_slots:
            replies.append(stitched_slots[i])
        else:
            replies.append(
                ReplyOption(
                    text="(generation incomplete — fallback reply)",
                    strategy_label="PATTERN INTERRUPT",
                    is_recommended=False,
                    coach_reasoning="(auto-generated fallback)",
                )
            )

    # Ensure exactly 1 recommended across the final combined array
    rec_count = sum(1 for r in replies if r.is_recommended)
    if rec_count == 0 and replies:
        replies[0] = replies[0].model_copy(update={"is_recommended": True})
    elif rec_count > 1:
        seen_first = False
        for i, r in enumerate(replies):
            if r.is_recommended:
                if seen_first:
                    replies[i] = r.model_copy(update={"is_recommended": False})
                else:
                    seen_first = True

    # Phase 5: prefer a strategy with a proven track record over the arbitrary
    # "lowest slot index wins" default above. Tries THIS conversation's own
    # history first (most specific), then falls back to what's landed for her
    # archetype across every conversation (Phase 3 — lets a brand-new match
    # benefit immediately instead of starting from zero). Both lists are
    # ranked best-first; take the first entry that matches one of the 4
    # strategies actually present this turn. If nothing in either list
    # matches (cold start, no data anywhere yet), the slot-order default
    # stands.
    preferred_strategies: list[str] = (
        conversation_context or {}
    ).get("preferred_strategies") or []
    archetype_preferred_strategies: list[str] = (
        conversation_context or {}
    ).get("archetype_preferred_strategies") or []
    combined_preferences = preferred_strategies + [
        label
        for label in archetype_preferred_strategies
        if label not in preferred_strategies
    ]
    for pref_label in combined_preferences:
        match_idx = next(
            (i for i, r in enumerate(replies) if r.strategy_label == pref_label),
            None,
        )
        if match_idx is None:
            continue
        if not replies[match_idx].is_recommended:
            for i, r in enumerate(replies):
                if r.is_recommended:
                    replies[i] = r.model_copy(update={"is_recommended": False})
            replies[match_idx] = replies[match_idx].model_copy(
                update={"is_recommended": True}
            )
        break

    # Pull out recommended strategy label to feed down the pipeline
    for r in replies:
        if r.is_recommended:
            recommended_strategy = r.strategy_label
            break

    # --- A/B shadow: run Groq on the SAME fan-out prompt set (first pass only) ---
    if _run_shadow and not is_rewrite:
        try:
            shadow_replies = _run_shadow_ensemble(
                state=state,
                analysis=analysis,
                shared_payload=shared_payload,
                assignments=assignments,
                llm_temperature=llm_temperature,
                phase="v2_generator_shadow_groq",
                use_groq=True,
            )
            logger.info(
                "v2_generator_ab",
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
                    for r in replies
                ],
                shadow_provider="groq",
                shadow_model=settings.groq_model,
                shadow_replies=[
                    {
                        "text": r.text,
                        "strategy_label": r.strategy_label,
                        "is_recommended": r.is_recommended,
                    }
                    for r in shadow_replies
                ],
            )
        except Exception:
            logger.warning(
                "v2_generator_ab_shadow_failed",
                        exc_info=True,
            )

    # --- Validate and fix ---
    gen_out = _stitch_generator_output(
        recommended_strategy_label=recommended_strategy,
        replies=replies,
    )
    gen_out = validate_and_fix_replies(gen_out)

    # Aggregate telemetry metrics for only the models that actually fired
    total_usage = {
        "phase": phase,
        "model": gen_model,
        "prompt_tokens": sum(r.get("prompt_tokens", 0) for r in usage_rows),
        "candidates_tokens": sum(r.get("candidates_tokens", 0) for r in usage_rows),
        "total_tokens": sum(r.get("total_tokens", 0) for r in usage_rows),
        "cost_usd": sum(float(r.get("cost_usd", 0) or 0) for r in usage_rows),
        "cost_inr": sum(float(r.get("cost_inr", 0) or 0) for r in usage_rows),
        "call_count": len(usage_rows),
    }

    logger.info(
        "generator_node_full_output",
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        phase=phase,
        recommended_strategy_label=gen_out.recommended_strategy_label,
        wrong_moves=[],
        right_energy="",
        hook_point="",
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
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        phase=phase,
        elapsed_ms=int((time.monotonic() - t_call) * 1000),
        recommended_strategy_label=gen_out.recommended_strategy_label,
        reply_count=len(gen_out.replies),
        fan_out_calls=len(usage_rows),
        usage_prompt_tokens=total_usage.get("prompt_tokens", 0),
        usage_candidates_tokens=total_usage.get("candidates_tokens", 0),
    )

    strategy = StrategyOutput(
        wrong_moves=[],
        right_energy="",
        hook_point="",
        recommended_strategy_label=gen_out.recommended_strategy_label,
    )
    drafts = WriterOutput(replies=gen_out.replies)

    return {
        "strategy": strategy,
        "drafts": drafts,
        "revision_count": revision_count + 1,
        "auditor_feedback": "",
        "is_cringe": False,
        "gemini_usage_log": [total_usage],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stitch_generator_output(
    recommended_strategy_label: str,
    replies: list[ReplyOption],
) -> "GeneratorOutput":  # type: ignore[name-defined]
    """Reconstruct GeneratorOutput from fan-out results."""
    from pydantic import BaseModel

    class StitchedOutput(BaseModel):
        recommended_strategy_label: str
        replies: list[ReplyOption]
        wrong_moves: list[str] = []
        right_energy: str = ""
        hook_point: str = ""

    return StitchedOutput(
        recommended_strategy_label=recommended_strategy_label,
        replies=replies,
    )


def _run_shadow_ensemble(
    *,
    state: AgentState,
    analysis: AnalystOutput,
    shared_payload: dict[str, Any],
    assignments: list[tuple[str, str]],
    llm_temperature: float,
    phase: str,
    use_groq: bool,
) -> list[ReplyOption]:
    """Run a shadow ensemble on Groq for A/B comparison. Best-effort."""
    import asyncio

    person_name = getattr(analysis, "person_name", None) or "unknown"
    direction = state.get("direction", "quick_reply")
    custom_hint = (state.get("custom_hint") or "").strip()
    photo_persona = getattr(analysis, "photo_persona", "") or ""
    transcript_text = transcript_text_from_analysis(analysis)
    detected_dialect = getattr(analysis, "detected_dialect", "ENGLISH") or "ENGLISH"

    async def _call(idx: int, hook: str, strategy: str):
        system_prompt = _build_single_line_prompt(
            person_name=person_name,
            direction=direction,
            detected_dialect=detected_dialect,
            transcript_text=transcript_text,
            assigned_hook=hook,
            assigned_strategy=strategy,
            custom_hint=custom_hint,
            photo_persona=photo_persona,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(shared_payload)),
        ]
        call_phase = f"{phase}_slot_{idx}"
        result, _ = invoke_structured_groq(
            model=settings.groq_model,
            temperature=llm_temperature,
            schema=SingleLineReply,
            messages=messages,
            phase=call_phase,
        )
        return idx, result

    tasks = [
        _call(idx, hook, strategy) for idx, (hook, strategy) in enumerate(assignments)
    ]
    raw = asyncio.run(asyncio.gather(*tasks, return_exceptions=True))

    replies: list[ReplyOption] = []
    sorted_items: list[tuple[int, Any]] = []
    for r in raw:
        if isinstance(r, Exception):
            continue
        sorted_items.append(r)
    sorted_items.sort(key=lambda x: x[0])

    first = True
    for idx, result in sorted_items:
        replies.append(
            ReplyOption(
                text=result.text,
                strategy_label=result.strategy_label,
                is_recommended=first,
                coach_reasoning=result.coach_reasoning,
            )
        )
        first = False

    while len(replies) < 4:
        fallback_labels: list[StrategyLabel] = [
            "PUSH-PULL",
            "FRAME CONTROL",
            "SOFT CLOSE",
            "VALUE ANCHOR",
            "PATTERN INTERRUPT",
        ]
        used = {r.strategy_label for r in replies}
        unused = [l for l in fallback_labels if l not in used]
        label = unused[0] if unused else "PATTERN INTERRUPT"
        replies.append(
            ReplyOption(
                text="(shadow fallback)",
                strategy_label=label,
                is_recommended=False,
                coach_reasoning="(shadow fallback)",
            )
        )
    return replies[:4]
