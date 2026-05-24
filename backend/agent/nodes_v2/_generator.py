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
from app.prompts.temperature import calculate_temperature
from app.prompts.templates.playbooks import select_playbook

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
# Core prompt template (archetype + direction rules are injected dynamically)
# ---------------------------------------------------------------------------

_GENERATOR_CORE_PROMPT = """
You are a dating text coach. Three phases: strategy → write 4 replies → self-check. Schema enforces structure — focus on psychology, tactics, dialect.

{custom_hint_section}
{dialect_enforcement}
{playbook_section}
PHASE 1: STRATEGY
* Source of truth: visual_transcript > core_lore.
* Double-text: If last bubble is from "user", do NOT re-answer her — build on user's last text.
* Upset/vulnerable tone: No heavy teasing. Mix: acknowledge (HONEST FRAME), pivot (FRAME CONTROL), question (PUSH-PULL). No 4 identical therapeutic replies.
* Dating goals/marriage topic: HONEST FRAME only. No banter.

PHASE 2: WRITE
* Format: no punctuation, lowercase ("dont", "im"). Match her length or shorter. For emotional contexts (go_deeper, de_escalate): keep sentences SHORT — real texting empathy is brief and raw. "that sounds brutal" > "being called careless in front of everyone must have been incredibly difficult". Long polished empathy sentences = sounds AI = fail.
* Diversity (CRITICAL): 4 replies = 4 different conversational paths. If they all mean the same thing, rewrite.
* Specificity: >=2 replies MUST embed exact words from top_hooks or her message in a SHORT punchy line. "the half marathon is just a biryani excuse isn't it" = PASS (brief, embeds both hooks). "training for a half marathon while being deeply committed to biryani sounds like a logistical nightmare" = FAIL (too long, polished, constructed-sounding). Echo must be brief, not a full sentence analysis.
* Freshness: Do NOT paraphrase last_ai_replies_shown. Treat as banned strings.
* No self-pivot: Never make it about yourself. Focus stays on her or the dynamic.

PHASE 3: SELF-CHECK (all 4 replies must pass)
* Grounded: Each reply needs verbatim anchor — quote her exact word or phrase with a twist. "you seem adventurous" = FAIL. "someone who gives 'goa' as their answer to everything" = PASS. "the 'not even close' is doing a lot of heavy lifting" = PASS. No invented assumptions about character without a quoted hook.
* Fork: Leave a SPECIFIC GAP she fills. Best formats: (a) expose a contradiction she'd deny ("claiming you dont plan when you probably spent weeks on tripadvisor"), (b) A/B hypothetical she picks ("would you have owned the wrong room or sprinted out"), (c) a claim about her specific action she corrects ("bet the ranked cafe list has footnotes"). NOT a punchline she laughs at — a GAP she fills with something specific.
* Quality bar: Replies 3+4 same quality as 1+2. Vague filler ("the chaos must have been productive") = FAIL.
* Claim attack ≠ character attack: Attack what she SAID, not who she IS. "claiming you dont plan while clearly having a plan" = PASS (attacks her CLAIM). "you sound like the type who..." / "you are the kind of person who..." = FAIL (character attack = nothing specific to push back against = fq=1-2 every time).
* Forbidden — therapy/corporate (SCAN EVERY REPLY — zero tolerance): "i appreciate", "i hear you", "i hear that", "i respect that", "i really value", "that sounds hard", "i understand where youre coming from", "thank you for sharing", "the fact that X says [anything] about Y", "the fact that you [did X] shows/says/means". These phrases = automatic rewrite regardless of direction.
* Forbidden — condescending: "adorable that you think", "commitment to being wrong", "anyone with a brain".
* Forbidden — openers: NEVER start with "hey/hi/so/well". No "haha/lol" opener unless reacting to a specific line.
* Forbidden — lazy: "what about you". No 2+ questions per reply.
* De-escalate check: If direction=de_escalate — (a) scan for banned phrases "i hear you / i appreciate / i respect that / that sounds / i understand where" → rewrite if found. (b) scan for question-first replies (reply leads with a question before naming what happened) → rewrite. Acknowledgment MUST come before any question.
* Go-deeper check: If direction=go_deeper — scan each reply: (a) question must follow acknowledgment, never precede it. (b) question subject must be HER inner experience: "what was going through your head in that moment" = PASS. "does he usually act like that" / "do you think your boss is normally like this" = FAIL (about the other person → rewrite).
* Get-number check: If direction=get_number — NEVER put a phone number, fake number, username, or contact detail inside reply text. The reply asks her to move off-app; it does NOT contain an actual number.
* Direction ban: No date/drink/number suggestions unless direction is ask_out or get_number.

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
* Restrictions: Do NOT be sincere or reassuring. If she accuses you playfully, do NOT confirm/deny. Suspend tension.
* Fork requirement: Every reply MUST leave an implicit or explicit response path — a claim she'd want to dispute, a challenge she'd want to accept, or a question mark hanging in the air. A pure brag ("i definitely have better X than you") with nothing to push back against = dead-end FAIL.""",
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
    * Requirement: Among moves to avoid, MUST include "being evasive" and "deflecting with humor".""",
    "THE EAGER/DIRECT": """
ARCHETYPE STRATEGY — THE EAGER/DIRECT:
* Context: Interested and moving forward.
* Labels: Prioritize SOFT CLOSE and FRAME CONTROL.
* Tone: Confident, warm, decisive. Match energy. Flirt back but lead toward logistics.
* Restrictions: Do NOT create artificial tension or play games.
* Requirement: At least one reply MUST include a concrete next step.""",
    "THE LOW-INVESTMENT": """
ARCHETYPE STRATEGY — THE LOW-INVESTMENT:
* Context: Short/flat reply — she's on autopilot or barely paying attention.
* Labels: Prioritize PATTERN INTERRUPT.
* Tone: Unbothered, high-standard. You're interesting — make her prove she can keep up.
* Restrictions: Do NOT over-explain or chase. Do NOT offer an exit ramp ("no stress if youre busy") — that kills any remaining chance. Match/undercut her length.
* Requirement: >=2 replies are bold, unexpected pattern interrupts — a statement, observation, or playful assumption she'd feel compelled to respond to. Make her lean in, not check out.""",
}

# ---------------------------------------------------------------------------
# Direction-specific prompt segments (only the relevant one is injected)
# ---------------------------------------------------------------------------

_DIRECTION_PROMPTS: dict[str, str] = {
    "opener": """
DIRECTION — OPENER:
* Hook priority: text_first = anchor on bio/story text. visual_first = spread distinct visual hooks. either = use strongest available.
* Goal: Playful assumption, callback, or sincere reaction — never a generic greeting.
* Banned: "hi/hey/hello", generic looks compliments, "hows your day".
* DIVERSITY: Each reply anchors on a DIFFERENT profile detail. 3-4 replies on the same detail = automatic fail.""",
    "quick_reply": """
DIRECTION — QUICK REPLY:
* Goal: Bounce ball back with a hook (tease, assumption, challenge). No dead statements.
* Ban: No date/drink/number suggestions — those belong in ask_out or get_number only.""",
    "keep_playful": """
DIRECTION — KEEP PLAYFUL:
* React to CONTENT not tone. Mine specific words, places, details — not her vibe.
* LOL/one-word rule: If last message is "lol/haha/ok" — ignore it. Make a FRESH BOLD STATEMENT from earlier thread content. FAIL: "that lol said everything". PASS: fresh observation from what she said earlier.
* Story rule: If mid-story, continue the story or self-deprecate — do NOT flip assumptions onto her ("you definitely have that look..."). Stays confrontational when she's low-effort.
* Each reply needs a specific pushback hook — bold assumption, light accusation, or unresolved claim.""",
    "change_topic": """
DIRECTION — CHANGE TOPIC:
* Pivot to a COMPLETELY NEW angle. Do NOT meta-comment on the dead topic ("weather is boring, let's change it" = still talking about weather = FAIL).
* If profile details exist: anchor the new topic to a specific profile/bio detail. If no profile info: introduce a completely fresh topic via a bold playful assumption about her personality, or a direct challenge/question that opens a new thread.
* DIVERSITY: All 4 replies open DIFFERENT doors. Not 3 replies all pivoting to the same new theme.
* Banned topics for pivot: pineapple pizza, zombie apocalypse, teleportation, lottery, generic travel.""",
    "tease": """
DIRECTION — TEASE:
* Goal: Cocky misinterpretation, observation, or challenge anchored to something she JUST said. Generic teases = banned.
* >=2 replies use PUSH-PULL or PATTERN INTERRUPT. No sensitive topics (looks, intelligence, family).
* Cover one per reply: MISINTERPRET (read a word the wrong way) / FLIP THE FRAME (accusation about her claim, not her character) / MOCK OUTRAGE (fake betrayal/disappointment). FLIP THE FRAME mocks what she SAID, not who she IS — "bold claim from someone who probably uses jarred sauce" = PASS. "you're clearly the type who..." = mocking character = FAIL.
* Fork test: Can she respond with more than "haha"? She must want to deny/defend/dispute with SPECIFICS. FAIL: "that explains so much honestly" (what does she say back?). PASS: "the 'not even close to restaurant level' — which restaurant, because if it's olive garden that bar is underground" (she has to defend her claim with a specific). Leave a gap she fills, not a punchline she just laughs at.
* DIVERSITY: All 4 teases attack DIFFERENT angles. One detail per reply.
* Banned: echoing her question back word-for-word; "tumhe kya lagta hai / tum hi batao".""",
    "revive_chat": """
DIRECTION — REVIVE CHAT:
* One per reply, all four tactics: (1) CALLBACK WITH TWIST — reference past chat with new angle. (2) FRESH OBSERVATION — bold claim from profile, act like no time passed. (3) CHALLENGE/BET — playful accusation she'd react to. (4) PATTERN INTERRUPT — unexpected opener, new thread.
* Variety: No 3+ replies using "you're the type to...". Vary structure.
* Banned: "hey stranger", "long time no speak", "sorry ive been mia".
* >=1 reference to core_lore/past_memories if available.
* Banned: "found/saw X and it reminded me of you", "this gave me deja vu of our conversation" — try-hard. Act like no time passed, not like you've been pining.""",
    "get_number": """
DIRECTION — GET NUMBER:
* Goal: Move off app. AT LEAST 3 of 4 replies must include an explicit off-app ask.
* Each ask must reference something specific from THIS conversation (joke, place, topic). Generic "this app is clunky" = low spec score.
* NEVER put a real or fake phone number / contact detail inside the reply text. You ask her to move; you don't provide a number.
* Banned app-fatigue lines (zero specificity, any match could receive these): "this app is where conversations go to die", "better conversations off this app", "apps kill good conversations". Off-app hook MUST reference something specific from THIS conversation.
* Banned ego openers: "reigning champion of your matches", "best youve seen", "i am the highlight of your inbox".
* Compliment redirect: If she complimented you, acknowledge it ONCE then pivot to off-app with a different hook. 2+ replies riffing on the same compliment = fail.
* GUARDED/TESTER exception: No pressure or confrontation. Warm, low-pressure HONEST FRAME. Still needs personality and a specific hook — "no pressure / feel free to" = momentum killer.""",
    "ask_out": """
DIRECTION — ASK OUT:
* AT LEAST 2 of 4 replies must include a concrete plan (specific activity + day/time). Other 2 can banter.
* Use her last message as the premise. "take me to your top spot this saturday" = PASS. "we should hang out sometime" = FAIL.""",
    "go_deeper": """
DIRECTION — GO DEEPER:
* Connection moment — she shared something real. Not banter. Show you actually heard her.
* Mix across 4 replies: (1) NAME THE SPECIFIC THING she said verbatim. (2) HONEST RAW REACTION — not advice or pep talk. (3) ONE CURIOUS QUESTION she'd actually want to answer — but acknowledgment MUST come first, question last. (4) GENTLE REFRAME — observation that shifts perspective without dismissing.
* Tone: Write like you're actually surprised and moved — raw over polished. Short over long. "that's heavy" > "i can see that this situation must have been very difficult for you." Constructed-sounding lines = FAIL.
* Fork requirement: EVERY reply still needs a response path — pure acknowledgment statements with no hook are dead-ends. Use: a feelings-focused question, a grounded observation she'd want to dispute/confirm, or a statement that implicitly invites her to say more.
* Question rule: Questions MUST (a) open with acknowledgment first, (b) ask about HER inner experience — NOT next steps, plans, or the other person. BAD: "what are you doing to clear your head tonight" (redirects), "does he usually act like that" (analyzes boss). GOOD: "what was the worst part of sitting through that", "was there anyone in the room who had your back". One question max per reply.
* Banned: advice, pep talks ("you've got this"), generic validation ("i totally understand"), implying she's overreacting ("are you going to let them ruin your week").
* Banned analytical phrases: "that says everything about you", "do you usually X when Y", "is this a one time thing".
* No redirecting to positivity before holding space first.""",
    "de_escalate": """
DIRECTION — DE-ESCALATE:
* Goal: Calm, grounded, real — not a therapist email.
* Banned phrases (scan every reply, rewrite if found): "i hear you", "i appreciate", "i respect that", "i really value", "that sounds hard/heavy", "i understand where youre coming from", "thank you for sharing".
* Instead: name the SPECIFIC event/behavior. "yeah i went quiet and that was on me" not "i hear you and i appreciate your honesty".
* Mix: (1) Own the specific thing. (2) Calm reframe/context. (3) Warm redirect forward. (4) Hold frame — one grounded sentence.
* Fork requirement: >=2 replies need a response hook — a forward-looking statement she can react to or a warm question after acknowledgment. WRONG: "you saying its fine when it clearly isnt is exactly what i dont like either" = calling out her behavior = still escalating. RIGHT: "yeah i dropped the ball on that, not gonna happen again" = owns it + opens space.
* No sarcasm, no dismissing ("chill/relax"), no PUSH-PULL or FRAME CONTROL labels.
* Question rule: CRITICAL — any reply with a question MUST open with acknowledgment of the specific thing that happened. Order is non-negotiable: acknowledge first → question last. A reply that opens with a question = automatic rewrite.""",
}


def _dialect_enforcement_block(detected_dialect: str) -> str:
    d = (detected_dialect or "ENGLISH").strip().upper()
    if d == "HINGLISH":
        return """DIALECT ENFORCEMENT: The detected dialect is HINGLISH. You MUST weave Romanized Hindi into EVERY reply (e.g., yaar, matlab, samajh, waisa, bilkul, thoda, bas, acha). ZERO purely standard-English replies are allowed — each line needs visible Hinglish texture that matches how she mixes languages. If you ship a reply that could be sent unchanged to an American texting in clean English only, you failed."""
    if d == "HINDI":
        return """DIALECT ENFORCEMENT: The detected dialect is HINDI. Match her level of English vs Hindi and her script choice; do not default to stiff textbook English or generic therapy English."""
    return """DIALECT ENFORCEMENT: The detected dialect is ENGLISH. No Romanized Hindi or Hinglish unless she clearly codeswitches that way. Casual lowercase style."""


def _build_generator_prompt(
    detected_archetype: str,
    direction: str,
    custom_hint: str,
    detected_dialect: str,
    stage: str = "early_talking",
    conversation_temperature: str = "warm",
    their_tone: str = "neutral",
    their_effort: str = "medium",
) -> str:
    """Build the generator system prompt with only the relevant archetype, direction, and playbook."""
    archetype_rules = _ARCHETYPE_PROMPTS.get(
        detected_archetype,
        _ARCHETYPE_PROMPTS["THE WARM/STEADY"],
    )
    direction_rules = _DIRECTION_PROMPTS.get(direction, "")
    hint = (custom_hint or "").strip()
    if hint:
        custom_hint_section = (
            "---\n"
            "USER-SPECIFIC REQUEST — HIGHEST PRIORITY\n"
            "---\n"
            f"The user asked for this angle (verbatim intent): {hint!r}\n"
            "- Strategy and all four replies MUST reflect this.\n"
            "- Do not treat it as optional flavor; it is the main creative brief.\n"
            "- Still ground replies in transcript_text and archetype rules.\n"
        )
    else:
        custom_hint_section = ""

    playbook = select_playbook(
        stage=stage,
        temperature=conversation_temperature,
        tone=their_tone,
        effort=their_effort,
    )
    playbook_section = playbook + "\n" if playbook else ""

    return _GENERATOR_CORE_PROMPT.format(
        archetype_rules=archetype_rules,
        direction_rules=direction_rules,
        custom_hint_section=custom_hint_section,
        dialect_enforcement=_dialect_enforcement_block(detected_dialect),
        playbook_section=playbook_section,
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
            "Do NOT just regenerate from scratch — improve the flagged replies.\n\n"
            f"{auditor_feedback}"
        )

    # --- Build conditional prompt (archetype + direction + playbook injected) ---
    detected_dialect = getattr(analysis, "detected_dialect", "ENGLISH") or "ENGLISH"
    their_tone = getattr(analysis, "their_tone", "neutral") or "neutral"
    their_effort = getattr(analysis, "their_effort", "medium") or "medium"
    system_prompt = _build_generator_prompt(
        detected_archetype=detected_archetype,
        direction=direction,
        custom_hint=custom_hint,
        detected_dialect=str(detected_dialect),
        stage=stage,
        conversation_temperature=conversation_temperature,
        their_tone=str(their_tone),
        their_effort=str(their_effort),
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
