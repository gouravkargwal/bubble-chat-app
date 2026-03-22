"""
Node 2: generator_node

Single Gemini call with structured output that performs:
  1. Strategy decision (wrong moves, right energy, hook point, label)
  2. Write 4 reply options
  3. On rewrites: incorporates auditor feedback to fix flagged replies

Model: gemini-3.1-flash-lite-preview with dynamic temperature
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
    truncate,
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
        description="ONE of: PUSH-PULL, FRAME CONTROL, SOFT CLOSE, VALUE ANCHOR, PATTERN INTERRUPT, HONEST FRAME"
    )

    # Writer output — exactly 4 reply options
    replies: list[ReplyOption] = Field(
        description="Exactly 4 reply options. Exactly ONE must have is_recommended=true."
    )


# ---------------------------------------------------------------------------
# Core prompt template (archetype + direction rules are injected dynamically)
# ---------------------------------------------------------------------------

_GENERATOR_CORE_PROMPT = """
You are a dating text coach. Your job is to:
  PHASE 1 — decide the psychological strategy (no reply text yet)
  PHASE 2 — write exactly 4 reply options
  PHASE 3 — self-audit and fix any cringe before outputting

You will be given a JSON payload with:
  analysis, direction, person_name, core_lore, past_memories, transcript_text,
  voice_dna_dict, conversation_context_dict

══════════════════════════════════════
PHASE 1 — STRATEGY
══════════════════════════════════════
Match Identity: Respond to [person_name].
The Lore: Use core_lore to maintain the established dynamic.
The Memories: Use past_memories to reference inside jokes ONLY if they fit naturally.
The Transcript: Base the immediate reply on transcript_text (her latest actual new message).

{archetype_rules}

ESCALATION ROUTING WHEN CHAT IS HOT:
- If conversation_temperature is "hot" AND her message mentions meet-up logistics,
  treat this as a closing moment. recommended_strategy_label should be "SOFT CLOSE".

THE INTENTIONS OVERRIDE:
- If transcript contains talk about dating goals, "what are you looking for", or marriage,
  the archetype should already be GUARDED/TESTER. If it isn't, treat it as one anyway.
  Drop all cocky/push-pull banter. Use HONEST FRAME.
  WRONG_MOVES must include being evasive about seriousness.

CONVERSION RULE:
- Do NOT generate "SOFT CLOSE" or ask for number unless their_effort is HIGH or temperature is HOT.
- If she is LOW-INVESTMENT or WARM/STEADY with medium effort, your ONLY goal is to spark curiosity.

STRATEGY LABELS:
- PUSH-PULL: create tension with a mix of interest and playful withdrawal
- FRAME CONTROL: lead the conversation frame, redefine the dynamic
- SOFT CLOSE: gently escalate toward plans, number, or meeting
- VALUE ANCHOR: show substance, depth, or social proof
- PATTERN INTERRUPT: break the current dynamic with something unexpected
- HONEST FRAME: be direct, sincere, and clear (for GUARDED/TESTER and DE-ESCALATE)

Fill: wrong_moves (2-3), right_energy, hook_point, recommended_strategy_label

══════════════════════════════════════
PHASE 2 — WRITE 4 REPLIES
══════════════════════════════════════
Each must use a clearly different psychological angle.

LANGUAGE LOCK:
- Write replies in the EXACT language/script/slang identified in detected_dialect.
- If detected_dialect is HINGLISH, reply in Romanized Hindi-English mix.
- If detected_dialect is ENGLISH, write casual lowercase English ONLY. No Hinglish words.
- Match their vocabulary. If they say "yaar", you can use "yaar".

STYLE RULE:
- NO PROPER PUNCTUATION. No apostrophes, commas, periods, exclamation marks, question marks.
- "dont" not "don't". "im" not "i'm". "youre" not "you're".
- Lowercase only. You are a lazy high-status texter, not an English professor.

LENGTH & MIRRORING:
- Match her message length or be slightly shorter. Single punchy sentence or phrase.
- If she gives low effort, be equally brief and unbothered.

THE TENSION SUSPENSION RULE:
- If she playfully accuses you of something, NEVER confirm or deny. Suspend the tension.

VIBE CONTINUITY:
- Optimize for the USER'S established texting persona from voice_dna_dict.
- Do NOT switch styles even if her language shifts.

FRESHNESS PENALTY:
- conversation_context_dict may include recent tactics. Do NOT repeat the same strategy or phrases.
- Force creative divergence across all 4 suggestions.

{direction_rules}

VOICE DNA & CONTEXT:
- voice_dna_dict: match length, emojis, capitalization, punctuation, favorite words. Never violate dislikes.
- conversation_context_dict: use history, avoid exhausted topics, keep persona consistent.

For each reply fill: text, strategy_label, is_recommended (exactly ONE true), coach_reasoning

══════════════════════════════════════
PHASE 3 — QUICK SELF-CHECK (before outputting)
══════════════════════════════════════
Scan your 4 replies for these SUBSTANTIVE issues only (punctuation is fixed by code):
- Does each reply actually respond to transcript_text? If one ignores her message → fix it.
- Does each reply match the archetype energy? If one uses sarcasm for GUARDED/TESTER → fix it.
- Does each reply follow the direction? If direction is "opener" and a reply has no visual_hook → fix it.
- Are all 4 replies genuinely different angles? If 3 feel the same → diversify the weakest one.
- Would a real person send this? If a reply sounds like therapy speak or corporate jargon → fix it.
"""

# ---------------------------------------------------------------------------
# Archetype-specific prompt segments (only the relevant one is injected)
# ---------------------------------------------------------------------------

_ARCHETYPE_PROMPTS: dict[str, str] = {
    "THE BANTER GIRL": """
ARCHETYPE STRATEGY — THE BANTER GIRL:
- She is actively sparring — sarcasm, tests, punchlines. Match her energy.
- Prioritize PUSH-PULL and PATTERN INTERRUPT.
- Tone: cocky, playful, unbothered. Tease her, misinterpret her in a funny way, or flip tests back.
- Do NOT be sincere or reassuring — she wants a sparring partner, not a therapist.
- If she accuses you of something playfully, do NOT confirm or deny. Suspend the tension.""",

    "THE INTELLECTUAL": """
ARCHETYPE STRATEGY — THE INTELLECTUAL:
- She sent a substantive message with a real topic. Engage with it.
- Prioritize VALUE ANCHOR and FRAME CONTROL.
- Tone: witty, thoughtful, culturally aware. Reference ideas, observations, or shared interests.
- Show depth without writing a lecture — match her message length.
- Avoid low-effort one-liners; they signal you dont match her investment.""",

    "THE WARM/STEADY": """
ARCHETYPE STRATEGY — THE WARM/STEADY:
- She is being normal, friendly, and engaged. This is the most common archetype.
- Mix strategies: use PUSH-PULL lightly, VALUE ANCHOR for substance, FRAME CONTROL to lead.
- Tone: confident but warm. You can tease lightly but the base energy is friendly and interested.
- Do NOT go full cocky/sarcastic — she is not testing you, she is just talking.
- Do NOT be overly sincere or serious either — keep it light and fun.
- This is where most conversations live. Be the fun, confident version of yourself.""",

    "THE GUARDED/TESTER": """
ARCHETYPE STRATEGY — THE GUARDED/TESTER:
- She is screening you. This is NOT banter — she wants a real answer.
- Prioritize HONEST FRAME and VALUE ANCHOR.
- Tone: high-status sincerity. Be clear, direct, and honest without oversharing.
- STRICT: Do NOT deflect, dodge, or joke your way out of the question. Evasion is low-status.
- STRICT: Do NOT use PUSH-PULL or sarcasm — she will read it as avoidance.
- Show you have standards and know what you want. Confidence comes from clarity, not mystery.
- One reply can add a light human touch after the honest answer ("but honestly...").
- wrong_moves MUST include "being evasive" and "deflecting with humor".""",

    "THE EAGER/DIRECT": """
ARCHETYPE STRATEGY — THE EAGER/DIRECT:
- She is clearly interested and moving forward. Do NOT play games.
- Prioritize SOFT CLOSE and FRAME CONTROL.
- Tone: confident, warm, decisive. Match her energy and close the deal.
- If she mentions meeting up, be specific with plans (place, time, activity).
- If she is flirting explicitly, flirt back but lead toward logistics.
- Do NOT tease or create artificial tension — she is past that stage.
- At least one reply should include a concrete next step.""",

    "THE LOW-INVESTMENT": """
ARCHETYPE STRATEGY — THE LOW-INVESTMENT:
- Her entire message was under 4 words of filler. She is on autopilot.
- Prioritize PATTERN INTERRUPT to shake her out of it, or "walk away" energy.
- Tone: unbothered, high-standard. Do NOT over-explain or chase.
- Keep your replies SHORT — match or undercut her length. Do NOT write a paragraph.
- At least one reply should make it easy to gracefully disengage ("no stress if youre busy").
- At least one reply should be a bold, unexpected pattern interrupt.""",
}

# ---------------------------------------------------------------------------
# Direction-specific prompt segments (only the relevant one is injected)
# ---------------------------------------------------------------------------

_DIRECTION_PROMPTS: dict[str, str] = {
    "opener": """
DIRECTION — OPENER:
- FORBIDDEN: Do NOT say "hi", "hey", "hello", or any greeting.
- Generate a "Reaction Comment" for her profile photo using visual_hooks from the analysis.
- A good comment is a playful assumption based on a specific visual detail.
- Example: "i bet you spent more time picking that camera than actually taking photos with it".
- Every reply MUST reference a concrete visual detail — generic openers are cringe.""",

    "quick_reply": """
DIRECTION — QUICK REPLY:
- Standard conversational reply. Respond naturally to what she said.
- No special constraints — let the archetype strategy guide the tone.""",

    "change_topic": """
DIRECTION — CHANGE TOPIC:
- Use LONG TERM MEMORY & PROFILE CONTEXT from conversation_context_dict as your ONLY source for new topics.
- BANNED: pineapple on pizza, zombie apocalypse, teleportation, winning lottery, generic travel questions.
- Study the topic exhaustion map and do NOT repeat listed themes.
- Pivot to a genuinely fresh, specific angle grounded in their actual profile or earlier chemistry.""",

    "tease": """
DIRECTION — TEASE:
- The goal is playful teasing — misinterpret something she said in a funny way, make a cocky observation,
  or lightly challenge her.
- Tone: cocky-funny, not mean. The tease should make her laugh or roll her eyes, not feel attacked.
- At least 2 replies should use PUSH-PULL or PATTERN INTERRUPT.
- Do NOT tease about sensitive topics (appearance, intelligence, family).""",

    "revive_chat": """
DIRECTION — REVIVE CHAT:
- The conversation has gone quiet. Your job is a high-energy fresh restart.
- You MAY reference her last text with a twist ("wait i just realized..." or "ok but you never told me...")
  IF it creates a natural callback. You may also ignore it entirely and go fresh.
- At least one reply should be a bold, unexpected angle (not "hey how are you").
- At least one reply should reference something from core_lore or past_memories if available.""",

    "get_number": """
DIRECTION — GET NUMBER / MOVE OFF APP:
- At least one reply MUST include a clear transition to moving off the app.
- Use casual style: "whatsapp pe switch karein", "drop your number", etc.
- If temperature is "hot", be more direct and confident.
- If temperature is "warm", frame the close as a natural next step, not a demand.
- Teasing is allowed ONLY if it still leads to an explicit "move off app" line in that reply.""",

    "ask_out": """
DIRECTION — ASK OUT:
- The goal is to ASK THEM OUT. Be specific with a concrete plan.
- Include a place, activity, or time suggestion — not just "we should meet".
- Match the vibe: if the conversation is playful, frame the ask-out playfully.
- At least one reply should be a bold, direct ask. At least one can be a softer suggestion.""",

    "de_escalate": """
DIRECTION — DE-ESCALATE:
- She is upset, annoyed, testing aggressively, or the conversation has gotten tense.
- STRICT: Do NOT match her negative energy. Do NOT get defensive or sarcastic.
- STRICT: Do NOT dismiss her feelings ("chill", "relax", "its not that deep").
- Prioritize HONEST FRAME and VALUE ANCHOR.
- Tone: calm, grounded, accountable where appropriate. Show emotional maturity.
- Acknowledge what she said without being a pushover.
- At least one reply should be a brief, sincere acknowledgment.
- At least one reply should gently redirect to positive ground.
- If she is testing (not genuinely upset), one reply can call it out calmly.""",
}


def _build_generator_prompt(detected_archetype: str, direction: str) -> str:
    """Build the generator system prompt with only the relevant archetype and direction rules."""
    archetype_rules = _ARCHETYPE_PROMPTS.get(
        detected_archetype,
        _ARCHETYPE_PROMPTS["THE WARM/STEADY"],
    )
    direction_rules = _DIRECTION_PROMPTS.get(direction, "")

    return _GENERATOR_CORE_PROMPT.format(
        archetype_rules=archetype_rules,
        direction_rules=direction_rules,
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
    t0 = time.monotonic()
    user_id = state.get("user_id", "")
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
    )

    detected_archetype = (
        getattr(analysis, "detected_archetype", "THE LOW-INVESTMENT")
        or "THE LOW-INVESTMENT"
    )

    logger.info(
        "agent_v2_generator_start",
        user_id=user_id,
        direction=direction,
        is_rewrite=is_rewrite,
        revision_count=revision_count,
        person_name=person_name,
        detected_archetype=detected_archetype,
        detected_dialect=getattr(analysis, "detected_dialect", None),
        their_effort=getattr(analysis, "their_effort", None),
        conversation_temperature=conversation_temperature,
        stage=stage,
        llm_temperature=llm_temperature,
        transcript_text=truncate(transcript_text, max_len=120),
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
    }

    semantic_profile = (
        voice_dna.get("semantic_profile") if isinstance(voice_dna, dict) else None
    )
    if semantic_profile:
        payload["USER_PSYCHOLOGICAL_STYLE_GUIDE"] = (
            f"CRITICAL — match this style in every reply: {semantic_profile}"
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
            "Do NOT just regenerate from scratch — improve the flagged replies.\n\n"
            f"{auditor_feedback}"
        )

    # --- Build conditional prompt (only relevant archetype + direction injected) ---
    system_prompt = _build_generator_prompt(detected_archetype, direction)

    t_call = time.monotonic()
    phase = "v2_generator_rewrite" if is_rewrite else "v2_generator"
    try:
        result, usage_row = invoke_structured_gemini(
            model=GENERATOR_MODEL,
            temperature=llm_temperature,
            schema=GeneratorOutput,
            messages=[
                SystemMessage(content=system_prompt),
                HumanMessage(content=json.dumps(payload)),
            ],
            phase=phase,
        )
        gen_out = cast(GeneratorOutput, result)
    except Exception as e:
        logger.error(
            "agent_v2_generator_llm_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            elapsed_ms=int((time.monotonic() - t_call) * 1000),
        )
        raise
    llm_ms = int((time.monotonic() - t_call) * 1000)

    # --- Validate reply count and fix if needed ---
    gen_out = validate_and_fix_replies(gen_out)

    # Build StrategyOutput and WriterOutput from GeneratorOutput
    strategy = StrategyOutput(
        wrong_moves=gen_out.wrong_moves,
        right_energy=gen_out.right_energy,
        hook_point=gen_out.hook_point,
        recommended_strategy_label=gen_out.recommended_strategy_label,
    )
    drafts = WriterOutput(replies=gen_out.replies)

    recommended_idx = next(
        (i for i, r in enumerate(gen_out.replies) if r.is_recommended), -1
    )

    logger.info(
        "agent_v2_generator_done",
        user_id=user_id,
        total_ms=int((time.monotonic() - t0) * 1000),
        llm_ms=llm_ms,
        llm_temperature=llm_temperature,
        is_rewrite=is_rewrite,
        reply_count=len(gen_out.replies),
        strategy_labels=[r.strategy_label for r in gen_out.replies],
        recommended_index=recommended_idx,
    )

    return {
        "strategy": strategy,
        "drafts": drafts,
        "revision_count": revision_count + 1,
        # Clear auditor feedback after consuming it
        "auditor_feedback": "",
        "is_cringe": False,
        "gemini_usage_log": [usage_row],
    }
