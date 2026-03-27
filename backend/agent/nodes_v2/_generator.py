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

from agent.nodes_v2._lc_usage import invoke_structured_gemini
from agent.nodes_v2._post_processor import validate_and_fix_replies
from agent.nodes_v2._shared import (
    GENERATOR_MODEL,
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
from app.prompts.temperature import calculate_temperature

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class GeneratorOutput(BaseModel):
    """Combined strategy + writer output from a single call with structured output."""

    # Strategy thinking
    wrong_moves: list[str] = Field(description="2-3 moves to avoid given the context.")
    right_energy: str = Field(description="Single best tone phrase.")
    hook_point: str = Field(description="The specific topic or detail to build around.")
    recommended_strategy_label: StrategyLabel = Field(
        description=(
            "ONE of: PUSH-PULL, FRAME CONTROL, SOFT CLOSE, VALUE ANCHOR, PATTERN INTERRUPT, HONEST FRAME. "
            "If double-texting, prioritize PATTERN INTERRUPT or VALUE ANCHOR to re-engage."
        )
    )

    # Writer output — exactly 4 reply options
    replies: list[ReplyOption] = Field(
        description="Exactly 4 reply options. Exactly ONE must have is_recommended=true."
    )


# ---------------------------------------------------------------------------
# Core prompt template (archetype + direction rules are injected dynamically)
# ---------------------------------------------------------------------------

_GENERATOR_CORE_PROMPT = """
You are a dating text coach. Process the input JSON payload in 3 sequential phases to generate exactly 4 distinct replies.

{custom_hint_section}

PHASE 1: STRATEGY & LOGIC
Analyze the payload. Output: wrong_moves (2-3), right_energy, hook_point, recommended_strategy_label.
* Source of Truth: visual_transcript > core_lore. If they conflict, trust the transcript.
* Double-Text Check: If analysis.their_last_message contains "[Note: User already replied with: ...]", DO NOT answer her previous message. Write a follow-up/nudge building on the user's last text.
* Archetypes & Overrides:
    * THE WARM/STEADY (Default): Friendly, engaged. Mix PUSH-PULL, VALUE ANCHOR, FRAME CONTROL. Light tease, but mostly fun/confident. NO heavy sarcasm/cockiness.
    * ESCALATION: If temperature="hot" AND mentions logistics -> "SOFT CLOSE".
    * INTENTIONS OVERRIDE: If talking dating goals/marriage -> Treat as GUARDED/TESTER. Use HONEST FRAME. wrong_moves: being evasive. No banter.
    * VULNERABLE OVERRIDE: If tone="upset"/"vulnerable" -> No teasing. Use HONEST FRAME/VALUE ANCHOR. Prioritize steadiness.
    * CONVERSION RULE: ONLY use "SOFT CLOSE" (or ask for number) if effort=HIGH or temperature=HOT. If LOW-INVESTMENT: spark curiosity, zero eager validation.
* Strategy Labels: PUSH-PULL (tension/interest/withdrawal), FRAME CONTROL (lead/redefine dynamic), SOFT CLOSE (escalate to plans/number), VALUE ANCHOR (substance/proof), PATTERN INTERRUPT (unexpected), HONEST FRAME (direct/sincere).

PHASE 2: WRITE 4 REPLIES
Output 4 reply objects: text, strategy_label, is_recommended (EXACTLY ONE true), coach_reasoning.
* Language & Style: Write EXACTLY in detected_dialect (ENGLISH = lowercase only, no Hinglish; HINGLISH = Romanized Hindi-English mix). Match their vocab (e.g., "yaar").
* Formatting: NO PROPER PUNCTUATION (no apostrophes, commas, periods, ? or !). Lowercase only ("dont", "im").
* Mirroring: Match her length or be shorter. Max 1 question per reply. If she gives low effort, give low effort back.
* Tactics:
    * Tension Suspension: NEVER confirm/deny playful accusations. Suspend tension.
    * Vibe Continuity: Use voice_dna_dict. Do not switch styles.
    * Freshness: Do not repeat conversation_context_dict tactics. 4 genuinely different angles.
    * Direction (Quick Reply): Standard reply, bounce ball back with a hook (tease, assumption, challenge). No dead statements.

PHASE 3: AUDIT & FILTER (Strict Constraints)
Before finalizing, ensure all 4 replies pass these checks:
* Relevant: Responds to transcript_text and honors user_custom_hint. Direction matches (e.g., "opener" uses a visual_hook).
* Grounded: No corporate/therapy speak. Cannot be a generic line sent to anyone (needs a concrete hook).
* Structured: Diverse shapes across the 4 replies. Each has an easy response path (fork test).
* Forbidden Phrases: No robotic fillers ("id love to", "i appreciate"). No dead openers ("hey", "hi", "so"). No starting with "haha", "hehe", "lol" unless directly reacting to a specific line. No lazy mirrors ("what about you"). No stacking 2+ questions.

{archetype_rules}

{direction_rules}
"""

# ---------------------------------------------------------------------------
# Archetype-specific prompt segments (only the relevant one is injected)
# ---------------------------------------------------------------------------

_ARCHETYPE_PROMPTS: dict[str, str] = {
    "THE BANTER GIRL": """
ARCHETYPE STRATEGY — THE BANTER GIRL:
* Context: Active sparring, sarcasm, tests. Match her energy.
* Labels: Prioritize PUSH-PULL and PATTERN INTERRUPT.
* Tone: Cocky, playful, unbothered. Tease, playfully misinterpret, or flip tests.
* Restrictions: Do NOT be sincere or reassuring. If she accuses you playfully, do NOT confirm/deny. Suspend tension.""",

    "THE INTELLECTUAL": """
ARCHETYPE STRATEGY — THE INTELLECTUAL:
* Context: Substantive message with a real topic. Engage with it.
* Labels: Prioritize VALUE ANCHOR and FRAME CONTROL.
* Tone: Witty, thoughtful, culturally aware. Reference ideas/observations.
* Restrictions: Match length to show depth. Avoid low-effort one-liners.""",

    "THE WARM/STEADY": """
ARCHETYPE STRATEGY — THE WARM/STEADY:
* Context: Friendly and engaged. Most common dynamic.
* Labels: Mix PUSH-PULL (lightly), VALUE ANCHOR, FRAME CONTROL.
* Tone: Confident, warm, fun. Light teasing is ok.
* Restrictions: NO heavy sarcasm/cockiness (she isn't testing you). NO overly serious sincerity.""",

    "THE GUARDED/TESTER": """
ARCHETYPE STRATEGY — THE GUARDED/TESTER:
* Context: She is screening you. Wants a real answer.
* Labels: Prioritize HONEST FRAME and VALUE ANCHOR.
* Tone: High-status sincerity. Clear and direct without oversharing.
* Restrictions: STRICT NO deflection/jokes. STRICT NO PUSH-PULL/sarcasm (reads as avoidance).
* Requirement: `wrong_moves` MUST include "being evasive" and "deflecting with humor".""",

    "THE EAGER/DIRECT": """
ARCHETYPE STRATEGY — THE EAGER/DIRECT:
* Context: Interested and moving forward.
* Labels: Prioritize SOFT CLOSE and FRAME CONTROL.
* Tone: Confident, warm, decisive. Match energy. Flirt back but lead toward logistics.
* Restrictions: Do NOT create artificial tension or play games.
* Requirement: At least one reply MUST include a concrete next step.""",

    "THE LOW-INVESTMENT": """
ARCHETYPE STRATEGY — THE LOW-INVESTMENT:
* Context: <4 words. Autopilot/filler.
* Labels: Prioritize PATTERN INTERRUPT.
* Tone: Unbothered, high-standard. 
* Restrictions: Do NOT over-explain or chase. Match/undercut her length.
* Requirement: >=1 reply gracefully disengages ("no stress if youre busy"). >=1 reply is a bold, unexpected pattern interrupt.""",
}

# ---------------------------------------------------------------------------
# Direction-specific prompt segments (only the relevant one is injected)
# ---------------------------------------------------------------------------

_DIRECTION_PROMPTS: dict[str, str] = {
    "opener": """
DIRECTION — OPENER:
* Goal: "Reaction Comment" for a photo using `visual_hooks`. Playful assumptions based on visual details.
* Restrictions: FORBIDDEN: "hi", "hey", "hello". FORBIDDEN: Generic looks compliments ("cute"). FORBIDDEN: Dead prompts ("hows your day"). 
* Requirement: 4 diverse hooks. Do not repeat the same detail.""",

    "quick_reply": """
DIRECTION — QUICK REPLY:
* Goal: Standard conversational reply based on the archetype.
* Requirement: Always bounce the ball back with a hook (tease, assumption, challenge). No dead statements.""",

    "change_topic": """
DIRECTION — CHANGE TOPIC:
* Goal: Pivot to a genuinely fresh, specific angle grounded in profile/chemistry.
* Source: Use ONLY `conversation_context_dict` for new topics. Do not repeat exhausted themes.
* Restrictions: BANNED topics: pineapple on pizza, zombie apocalypse, teleportation, winning lottery, generic travel.""",

    "tease": """
DIRECTION — TEASE:
* Goal: Cocky-funny misinterpretation, cocky observation, or light challenge.
* Labels: >=2 replies MUST use PUSH-PULL or PATTERN INTERRUPT.
* Restrictions: Do NOT tease sensitive topics (looks, intelligence, family).""",

    "revive_chat": """
DIRECTION — REVIVE CHAT:
* Goal: High-energy fresh restart.
* Tactics: Callback with a twist ("wait i just realized...") OR completely fresh. 
* Restrictions: BANNED lines: "hey stranger", "long time no speak", "sorry ive been mia".
* Requirement: >=1 bold/unexpected angle. >=1 reference to core_lore/past_memories (if available).""",

    "get_number": """
DIRECTION — GET NUMBER / MOVE OFF APP:
* Goal: Move off the app.
* Tactics: Casual style ("drop your number", "whatsapp pe switch karein"). Hot = direct. Warm = natural next step.
* Restrictions: AVOID stiff asks without context ("can i get your number"). Teasing ONLY allowed if it ends in an off-app move.
* Requirement: >=1 reply MUST explicitly transition off-app.""",

    "ask_out": """
DIRECTION — ASK OUT:
* Goal: Concrete plan (place, activity, or time). Not just "we should meet". Match the current vibe.
* Restrictions: AVOID formal/vague lines ("would you like to go on a date", "hang out sometime").
* Requirement: >=1 bold, direct ask. >=1 softer suggestion.""",

    "de_escalate": """
DIRECTION — DE-ESCALATE:
* Goal: Handle tension, tests, or upset feelings calmly. Show emotional maturity.
* Labels: Prioritize HONEST FRAME and VALUE ANCHOR.
* Restrictions: STRICT NO sarcasm/matching negative energy. STRICT NO dismissing ("chill"). 
* Requirement: MUST lead with acknowledgment before pivoting (rewrite if missing). >=1 sincere acknowledgment. >=1 gentle redirect.""",
}


def _build_generator_prompt(
    detected_archetype: str, direction: str, custom_hint: str
) -> str:
    """Build the generator system prompt with only the relevant archetype and direction rules."""
    archetype_rules = _ARCHETYPE_PROMPTS.get(
        detected_archetype,
        _ARCHETYPE_PROMPTS["THE WARM/STEADY"],
    )
    direction_rules = _DIRECTION_PROMPTS.get(direction, "")
    hint = (custom_hint or "").strip()
    if hint:
        custom_hint_section = (
            "══════════════════════════════════════\n"
            "USER-SPECIFIC REQUEST — HIGHEST PRIORITY\n"
            "══════════════════════════════════════\n"
            f"The user asked for this angle (verbatim intent): {hint!r}\n"
            "- Strategy (wrong_moves, hook_point) and all 4 replies MUST reflect this.\n"
            "- Do not treat it as optional flavor; it is the main creative brief.\n"
            "- Still ground replies in transcript_text and archetype rules.\n"
        )
    else:
        custom_hint_section = ""

    return _GENERATOR_CORE_PROMPT.format(
        archetype_rules=archetype_rules,
        direction_rules=direction_rules,
        custom_hint_section=custom_hint_section,
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

    detected_archetype = (
        getattr(analysis, "detected_archetype", "THE LOW-INVESTMENT")
        or "THE LOW-INVESTMENT"
    )

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
            "Do NOT just regenerate from scratch — improve the flagged replies.\n\n"
            f"{auditor_feedback}"
        )

    # --- Build conditional prompt (only relevant archetype + direction injected) ---
    system_prompt = _build_generator_prompt(detected_archetype, direction, custom_hint)

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
        context_interaction_count=interaction_count if isinstance(interaction_count, int) else 0,
        has_voice_dna=bool(voice_dna),
    )
    logger.info(
        "llm_lifecycle",
        stage="generator_node_pre_llm",
        trace_id=trace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        direction=direction,
        model=GENERATOR_MODEL,
        phase=phase,
        payload_keys=sorted(payload.keys()),
        payload_replies_count=len((payload.get("previous_replies") or {}).get("replies", []))
        if isinstance(payload.get("previous_replies"), dict)
        else 0,
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
        model=GENERATOR_MODEL,
        messages=sanitize_llm_messages_for_logging(messages),
    )

    try:
        result, usage_row = invoke_structured_gemini(
            model=GENERATOR_MODEL,
            temperature=llm_temperature,
            schema=GeneratorOutput,
            messages=messages,
            phase=phase,
        )
        gen_out = cast(GeneratorOutput, result)
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
