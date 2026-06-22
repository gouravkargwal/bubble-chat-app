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
from agent.nodes_v2._personality import build_tone_prior
from agent.nodes_v2._post_processor import validate_and_fix_replies
from agent.nodes_v2._shared import (
    BANNED_EXAMPLE_PHRASES,
    GENERATOR_MODEL,
    SCAFFOLD_RULE,
    STRATEGY_LABEL_GLOSSARY,
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

{strategy_glossary}

RIZZ BAR — READ FIRST (applies to EVERY direction EXCEPT de_escalate and go_deeper, and is SUSPENDED whenever her tone is upset/vulnerable — there, warmth and acknowledgment win, never force a spike):
"Safe" kills attraction. A grounded, polite, correct reply that any nice guy could send = FAIL, even if it breaks zero rules. EVERY reply must carry a SPIKE — at least one of:
* a BOLD PLAYFUL ASSUMPTION about something she DOES, she'll want to correct ("you're the type who rates every cafe out of 10 and has notes") — anchor it to a BEHAVIOR/HABIT she can deny, NEVER a verdict on who she IS (banned: "you're the artsy/filmy type", "you've got influencer energy", "scorpio so you think everyone's wrong")
* a light DISQUALIFICATION / challenge ("not convinced you'd survive a weekend off your phone")
* a COCKY, UNBOTHERED frame that makes HER qualify ("ill allow the bike pic but you'll have to prove you actually ride")
* a real STANCE / hot take — pick a side, don't ask a neutral question
BANNED as a whole reply (this is "good boy" filler): pure observation ("the cafe looks nice"), neutral interview questions ("whats your favorite X", a flat "a or b" with no assumption baked in), validation ("makes sense you want long-term"), small talk.
Confidence beats correctness. SINCERE / TRADITIONAL ≠ SAFE: an earnest or traditional archetype still needs a REAL cocky tease, a playful challenge, or a bold assumption (tease how seriously/methodically she takes things, set a "you have to earn it" frame, make HER qualify) — going soft and sincere back at her is the #1 cause of bland "good boy" replies. The only difference vs other archetypes: don't be crude and don't mock her actual values/religion/background. A confident smirk and a "prove it" are exactly right.
DEFAULT BOLDER: when torn between a polite version and a cockier version, pick the cockier one. At least 2 of the 4 replies must land as a genuine tease / challenge / bold claim a confident guy would send — NOT a polite question.

SOUND HUMAN, NOT AI — READ SECOND (every direction; this is what makes a reply feel like a real person texting instead of a bot):
* SHORT IS A RULE, NOT A SUGGESTION. Aim ~6-12 words. If a reply needs a comma, a "that/who/which" clause, or a "but/so/or" to hold itself together, it is TOO LONG — cut to the punch. A 20+ word line is an essay, not a text, and reads as AI no matter how clever.
* FIRE THE SPIKE AND STOP. Do not explain the joke or trail an extra clause. "bet your cafe list has rankings" (stop) NOT "bet your cafe list has rankings you defend to anyone who disagrees". The explaining clause is exactly what kills it.
* TEXTED, NOT WRITTEN. Thumbs on a phone, not a sentence composed for an essay. Fragments win. A grammatically-complete, balanced sentence is an AI tell.
* NO AI SCAFFOLDS (the #1 "sounds like a bot" tell — never OPEN with one): {scaffold_rule}
* STRANGER RULE: a long observational read of who she is = presumptuous AND robotic. A quick tease about one thing she DID lands; a four-clause psychoanalysis does not.
* ANCHOR TO HER — NO GENERIC CRUTCHES (every direction): every reply MUST hook something SHE actually said or shows. LITMUS: strip her specifics — if the line could be sent to ANY match, it's a generic crutch → rewrite it to her real words. Banned crutches: imported hypotheticals/tropes (zombie apocalypse, desert island, if you won the lottery, teleportation, stranded on an island, "two truths and a lie") and lazy zodiac-personality reads (capricorn/scorpio so you're X). Teasing her ACTUAL words ("avoiding hostels at all costs" → "character building is overrated when room service exists") always beats a clever line that ignores the conversation.

PHASE 1: STRATEGY
* Source of truth: visual_transcript > core_lore.
* LIVE MOMENT > profile facts: mid-chat, the thing she JUST engaged with — a joke she laughed at, a point she just made — is the LIVE THREAD. EXTEND or FLIP it before re-mining profile facts. If she laughed at your bit, ride/flip THAT bit (e.g. she laughs at your "you fail guys' inspection" joke → flip it: "so do i pass inspection or am i on the reject pile") — do NOT reset to an unrelated fresh profile-fact tease. Profile-fact assumptions are the FALLBACK (openers, or when she gave nothing to grab).
* Read user_last_move FIRST. If the user's own last reply was low-effort (generic compliment, one-word, "haha", "nice") and her latest message cooled or shortened in response, the weak link was the USER — NOT her. Do NOT mock her, accuse her of being fake/dismissive, or treat her as low-investment for a drop the user caused. RECOVER: re-engage her last substantive point with genuine interest. This holds even when direction=tease — tease the awkward beat or the situation (even self-aware about the weak reply), NEVER her sincerity.
* Inbound image: read inbound_image. If "selfie_of_her" — she sent a photo of HERSELF (interest/escalation signal): react warmly and you MAY escalate; never ignore the image, and never describe her in a clinical/creepy way ("nice symmetrical face"). If "object_or_scene" — she shared a thing/moment (coffee, pet, food, view, meme): react to the THING and fold it into the banter; NEVER compliment her looks (there is no "her" in the image to compliment). If "none" — normal text chat.
* Double-text: If last bubble is from "user", do NOT re-answer her — build on user's last text.
* Upset/vulnerable tone: No heavy teasing. Mix: acknowledge (HONEST FRAME), pivot (FRAME CONTROL), question (PUSH-PULL). No 4 identical therapeutic replies.
* Dating goals/marriage topic: you MAY tease it with a cocky/playful frame — mock-panic at the seriousness, set a "you'll have to earn it" frame, make her qualify. What you must NOT do is neg the goal itself (calling long-term desperate/overrated/too-much) or get crude. Go full HONEST FRAME ONLY if SHE raises it vulnerably or heavily.

PHASE 2: WRITE
* Format: no punctuation, lowercase ("dont", "im"). Match her length or shorter. For emotional contexts (go_deeper, de_escalate): keep sentences SHORT — real texting empathy is brief and raw. "that sounds brutal" > "being called careless in front of everyone must have been incredibly difficult". Long polished empathy sentences = sounds AI = fail.
* Diversity (CRITICAL): 4 replies = 4 DIFFERENT specific hooks, never 4 rewordings of one (NOT all four on her "long-term" goal or one photo). When ONE hook dominates (e.g. her job), do NOT let 3+ replies pile onto it — force the other replies onto different details. On sparse photo-heavy profiles, spread across distinct visual details — an outfit vs a setting vs a styling contrast (a specific CHOICE is fine; generic looks compliments like "you're gorgeous" are not).
* Specificity: >=2 replies MUST embed her exact words (from top_hooks or her message) — a brief echo, not a sentence-long analysis.
* Freshness: Do NOT paraphrase last_ai_replies_shown. Treat as banned strings.
* No self-pivot — but frame-flips are allowed: don't make it about your life or qualify yourself ("i love hiking too", "as an engineer i..."). BUT a PLAYFUL frame-flip that rides HER own joke back onto the dynamic IS allowed banter — making her playfully judge/rate you ("so do i pass your inspection or am i on the reject pile") is a tease, NOT a self-pivot. The line: tongue-in-cheek "you judge me" built from her bit = good; earnest self-disclosure = banned.
{banned_examples}

PHASE 3: SELF-CHECK (all 4 must pass; all 4 equal quality — 3+4 are not filler):
* Re-scan each reply against the rules above: it has a SPIKE (RIZZ BAR); it's SHORT + texted + anchored to HER words with no scaffold/generic-crutch (SOUND HUMAN); it teases what she DOES, never a verdict on who she IS — character/aesthetic/zodiac label = the #1 auto-reject (attacking a CLAIM she made is always fine); and it leaves a FORK — a specific gap she fills (a contradiction she'd deny, an A/B she picks, or a claim she corrects), NOT a punchline she just laughs at.
* Label accuracy: each strategy_label MUST match the text per the DEFINITIONS above (an "A or B" question = FRAME CONTROL; pure validation = HONEST FRAME). Fix the label, never force it.
* Persona: photo_persona shapes TONE + spots outfit/setting hooks — never a looks/identity verdict ("influencer energy", "artsy type" = FAIL); a specific CHOICE she made (outfit, setting) is fine.
* Banned (zero tolerance — scan every reply, rewrite if found): therapy/validation — "i appreciate / i admire / i hear you / i respect that / i really value / i love that / that sounds hard / thank you for sharing / the fact that you X shows/means Y", and ANY "i [appreciate/admire/respect/love/value/honor] the/your ___"; condescending — "adorable that you think", "anyone with a brain"; dead openers — "hey/hi/so/well" (and "haha/lol" unless reacting to a specific line); lazy — "what about you", or 2+ questions in one reply.
* Direction order checks: de_escalate & go_deeper → acknowledgment BEFORE any question (question-first = rewrite); go_deeper questions ask about HER inner experience, not the other person or next steps; get_number → never put an actual number in the reply; no date/drink/number unless direction is ask_out or get_number.

---
CURRENT CONVERSATION — everything above is the fixed playbook; apply it to THIS specific situation:
- conversation_context_dict.recent_summaries (when present) is the VERBATIM recent thread — her actual words and exactly what you already sent. Treat it as the real running conversation: build on it, stay consistent with it, and never repeat or contradict what was already said.
- core_lore (when present) is WHAT YOU ALREADY KNOW ABOUT HER from past chats (durable facts). Sound like you remember her: never ask about something already in core_lore, and weave a known detail in naturally when it fits.
{dialect_enforcement}
{playbook_section}
{personality_prior}
{direction_rules}
{learned_strategy_section}
{custom_hint_section}
"""

# ---------------------------------------------------------------------------
# Direction-specific prompt segments (only the relevant one is injected)
# ---------------------------------------------------------------------------

_DIRECTION_PROMPTS: dict[str, str] = {
    "opener": """
DIRECTION — OPENER:
* Hook priority: text_first = bio/story text. visual_first = photo hooks. either = strongest. Weak profile (only trait tags, no real prompt answers) → treat photo hooks as primary anchor.
* Banned: "hi/hey/hello", looks compliments, "hows your day", generic compliment + question combos.
* ATTACK ANGLE DIVERSITY — 4 replies must cover different angles:
  1. BOLD ASSUMPTION — claim how she behaves based on one specific detail (tease what she DOES)
  2. FLIP HER WORDS — take her exact prompt answer and challenge or question it directly
  3. PHOTO CALLBACK — tease a specific visual observation (outfit choice, setting, expression, background detail)
  4. SINCERE REACTION — genuine non-sycophantic response to something specific she wrote (not a compliment, a real reaction)
* TONE SPREAD: ≥1 reply warm/curious, ≥1 reply playful/cocky. Not all 4 at the same register.""",
    "quick_reply": """
DIRECTION — QUICK REPLY:
* Goal: Bounce ball back with a hook (tease, assumption, challenge). No dead statements.
* LIVE MOMENT FIRST: ride her last actual words before mining profile facts. Only fall back to profile-fact assumptions when she gave nothing to grab.
* LOW-EFFORT / ONE-WORD rule: "haha/lol/ok/nice/wow" or single emoji — ignore that token. Make a FRESH BOLD STATEMENT from earlier thread content. FAIL: "haha glad you liked it".
* Frame-flips allowed: riding her own joke back ("so do i pass your inspection") is banter, not self-pivot. Earnest self-disclosure = banned.
* BANTER vs CONNECTION: EAGER/DIRECT + high effort + sharing real details = CONNECTION mode. Meet sincerity with warm curiosity + a light hook, not a cocky tease.
* Ban: No date/drink/number suggestions — those belong in ask_out or get_number only.""",
    "keep_playful": """
DIRECTION — KEEP PLAYFUL:
* React to CONTENT not tone. Mine specific words, places, details — not her vibe.
* LOL/one-word rule: If last message is "lol/haha/ok/totally/nice" — ignore it. Make a FRESH BOLD STATEMENT from earlier thread content. FAIL: "that lol said everything". PASS: fresh observation from what she said earlier.
* Story rule: If mid-story, continue the story or self-deprecate — do NOT flip assumptions onto her ("you definitely have that look..."). Stays confrontational when she's low-effort.
* Frame-flips are allowed: if she just laughed at your joke or validated something you said, riding that back ("so do i pass your inspection or not") IS allowed banter — not self-pivot. Use it when she's given you a warm signal and you want to escalate the dynamic slightly.
* Each reply needs a specific pushback hook — bold assumption, light accusation, unresolved claim, or frame-flip.
* Banned strategy labels in this direction: SOFT CLOSE — keep_playful is banter only, no closing/date/number moves.
* ATTACK ANGLE DIVERSITY — the 4 replies must use different angles, not all personality commentary. Rotate across:
  1. QUESTION HER LOGIC — poke a hole in what she said ("thanda paani se kya fark padta hai yaar"). No drama, just deadpan.
  2. SARCASTIC AGREE + FLIP — agree with her premise, then turn it back ("haan makes sense, matlab tum khud apni dushmaan ho").
  3. MAKE IT ABOUT YOU — insert yourself into her situation ("toh main safe hu kya tumhare aas paas").
  4. MOCK THE DETAIL — zoom into one specific word/detail she used and make it absurd ("thanda paani — full scientific approach hai tera").
* Banned intensifiers as lazy defaults: "dangerous", "chaos", "intense" — these are vague dramatic labels. Only use them if her EXACT words contain that energy. Instead reach for specific, mundane observations about what she actually said.""",
    "change_topic": """
DIRECTION — CHANGE TOPIC:
* Pivot to a COMPLETELY NEW angle. Do NOT meta-comment on the dead topic ("weather is boring, let's change it" = still talking about weather = FAIL).
* If profile details exist: anchor the new topic to a specific profile/bio detail. If no profile info: introduce a completely fresh topic via a bold playful assumption about her personality, or a direct challenge/question that opens a new thread.
* DIVERSITY: All 4 replies open DIFFERENT doors. Not 3 replies all pivoting to the same new theme.
* Banned pivot topics — overused app clichés that any match could receive:
  - Food debates with no profile anchor: pineapple pizza, "chai vs coffee person"
  - Generic hypotheticals: zombie apocalypse, desert island, teleportation, lottery win
  - Personality test clichés: "what's your love language", "what's your enneagram", "if you were an animal/fruit/season"
  - Generic travel: "where do you want to travel" with no profile anchor (travel anchored to HER specific city/trip/plans is fine)
  - App meta-commentary: "this app is weird", "matching is random"
  A good pivot is specific to HER profile or the running conversation — not a topic you'd send to any match.""",
    "tease": """
DIRECTION — TEASE:
* Goal: Cocky misinterpretation, observation, or challenge anchored to something she JUST said. Generic teases = banned.
* >=2 replies use PUSH-PULL or PATTERN INTERRUPT. No sensitive topics (looks, intelligence, family).
* Cover one per reply: MISINTERPRET (read a word the wrong way) / FLIP THE FRAME (accusation about her claim, not her character) / MOCK OUTRAGE (fake betrayal/disappointment) / CALLOUT (directly dispute or challenge a claim she made). FLIP THE FRAME mocks what she SAID, not who she IS — "bold claim from someone who probably uses jarred sauce" = PASS. "you're clearly the type who..." = mocking character = FAIL.
* Fork test: Can she respond with more than "haha"? She must want to deny/defend/dispute with SPECIFICS. Leave a gap she fills, not a punchline she just laughs at.
* DIVERSITY: All 4 teases attack DIFFERENT angles. One detail per reply.
* Banned: echoing her question back word-for-word; "tumhe kya lagta hai / tum hi batao"; generic food/culture debates not anchored to HER words (pineapple pizza, chai vs coffee, "hot or cold water person").""",
    "revive_chat": """
DIRECTION — REVIVE CHAT:
* One per reply, all four tactics: (1) CALLBACK WITH TWIST — reference past chat with new angle. (2) FRESH OBSERVATION — bold claim from profile, act like no time passed. (3) CHALLENGE/BET — playful accusation she'd react to. (4) PATTERN INTERRUPT — unexpected opener, new thread.
* WHY DID IT DIE — check user_last_move first: if the chat went cold because the user's OWN last reply was weak/low-effort (not her going cold on a good reply), lean toward CALLBACK WITH TWIST or a self-aware PATTERN INTERRUPT. A light self-aware beat ("that last reply was rough, let me try again") is allowed — it shows awareness without being needy. Do NOT blame her for the drop or mock her for going quiet.
* Variety: No 3+ replies using "you're the type to...". Vary structure.
* Banned: "hey stranger", "long time no speak", "sorry ive been mia", "been busy lately".
* >=1 reference to core_lore/past_memories if available.
* Banned: "found/saw X and it reminded me of you", "this gave me deja vu" — try-hard. Act like no time passed.""",
    "get_number": """
DIRECTION — GET NUMBER:
* Goal: Move off app. AT LEAST 3 of 4 replies must include an explicit off-app ask anchored to something specific from THIS conversation.
* Each ask must reference something from the conversation (joke, place, topic). Generic "this app is clunky" = FAIL.
* NEVER put a real or fake phone number / contact detail inside the reply text.
* PLATFORM — match friction to her warmth:
  - Warm/hot: WhatsApp or number is fine — confident direct ask.
  - Lukewarm/guarded: Instagram is lower-friction (she doesn't give you her number, just a handle) — prefer IG for reserved archetypes. "drop your insta" lands softer than "give me your number".
* CITY LOGISTICS — if city unknown or she's not in the same city: asking for a number with no plan to meet is premature. In that case, the ask should be for social (IG/WhatsApp) for continued conversation, not a "let's meet" number ask.
* Banned app-fatigue lines: "this app is where conversations go to die", "better conversations off app", "apps kill conversations" — zero specificity, any match could receive these.
* Banned ego openers: "reigning champion of your matches", "best youve seen", "highlight of your inbox".
* Compliment redirect: acknowledge once, pivot off-app with a different hook. Don't riff on the compliment 2+ replies.
* GUARDED/TESTER exception: Warm, low-pressure — prefer IG over number. No "no pressure / feel free to" — momentum killer.""",
    "ask_out": """
DIRECTION — ASK OUT:
* Goal: move from app to real life. AT LEAST 2 of 4 replies must include an explicit off-app ask with a specific activity. Other 2 can banter or set a frame.
* Anchor the ask to THIS conversation: the activity or premise MUST reference something she said, did, or the running joke — NOT a generic "coffee?" with no connection. "chalo let me test your heat tolerance this saturday for coffee" (anchored to her heat story) = PASS. "we should hang out sometime" = FAIL (generic, zero connection).

* DAY SPECIFICITY — read conversation_temperature:
  - conversation_temperature = warm or hot → include a specific day (saturday, this weekend, friday evening). Confidence lands well when she's already engaged.
  - conversation_temperature = lukewarm or cold → use "this week" or "you pick the day" instead of a hard day. Forcing a specific day on a lukewarm match feels presumptuous — give her room to respond without committing to a calendar slot first.

* LOGISTICS — read core_lore for city:
  - Same city → propose a specific spot type or area (coffee in [her city], brunch somewhere she'd know). She can visualize it.
  - Different city or city unknown → skip the specific day entirely. Ask "next time you're in [city]" or float the logistics first ("are you based in delhi or elsewhere?") — one logistics reply in the batch is fine.

* TONE: confident but not heavy. The ask should feel like the natural next move, not a formal request. Ride the live joke or banter thread into the ask — the activity should feel like an extension of what you were already talking about.
* BANNED: "would you like to", "if you're free", "no pressure", "maybe sometime" — hedging kills momentum. Ask like you expect yes.
* BANNED ego openers: "reigning champion of your matches", "best you've seen".
* Compliment redirect: if she complimented you, acknowledge once then pivot to the ask with a different hook.""",
    "go_deeper": """
DIRECTION — GO DEEPER:
* Connection moment — she shared something real. Not banter. Show you actually heard her.
* Each reply uses a DIFFERENT move — one per reply, no repeats:
  1. NAME THE THING — echo her exact words back, nothing else ("lamba din" / "bohot thak gayi")
  2. RAW REACTION — your honest gut response, no advice, no solution ("uff that sounds brutal")
  3. CURIOUS QUESTION — acknowledgment first, then one inner-experience question (what was the worst part / was anyone in your corner)
  4. GENTLE REFRAME — observation that shifts perspective without dismissing what she felt
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
    direction: str,
    custom_hint: str,
    detected_dialect: str,
    stage: str = "early_talking",
    conversation_temperature: str = "warm",
    their_tone: str = "neutral",
    their_effort: str = "medium",
    preferred_strategies: list[str] | None = None,
    personality_prior: str = "",
) -> str:
    """Build the generator system prompt.

    The DRIVER is the situational policy (direction × stage × her tone, via the
    playbook + direction rules). The personality read is injected only as a light
    tone prior that is explicitly subordinate to the situational rules.
    """
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
            "- Still ground replies in transcript_text and the situational rules.\n"
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

    # Phase 5: bias toward strategies that have landed with HER specifically,
    # learned from copy-rate + her engagement response. Advisory, not a mandate —
    # the archetype/direction rules still govern correctness.
    clean_strategies = [s for s in (preferred_strategies or []) if s and s.strip()]
    if clean_strategies:
        learned_strategy_section = (
            "WHAT'S WORKED WITH HER (learned): "
            + ", ".join(clean_strategies)
            + ". Lean toward these strategy types when they fit the moment — "
            "they've earned replies from her before. Do not force one if it "
            "clashes with the current context.\n"
        )
    else:
        learned_strategy_section = ""

    return _GENERATOR_CORE_PROMPT.format(
        personality_prior=personality_prior,
        direction_rules=direction_rules,
        custom_hint_section=custom_hint_section,
        dialect_enforcement=_dialect_enforcement_block(detected_dialect),
        playbook_section=playbook_section,
        learned_strategy_section=learned_strategy_section,
        strategy_glossary=STRATEGY_LABEL_GLOSSARY,
        banned_examples=BANNED_EXAMPLE_PHRASES,
        scaffold_rule=SCAFFOLD_RULE,
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
        and str(stable_archetype).strip().upper() != str(detected_archetype).strip().upper()
    ):
        logger.info(
            "archetype_stabilized_override",
            scan_archetype=detected_archetype,
            stable_archetype=stable_archetype,
            confidence=archetype_confidence,
        )
        detected_archetype = str(stable_archetype)

    # Phase 5: strategies that have landed with her before (copy + conversion).
    preferred_strategies = (conversation_context or {}).get("preferred_strategies") or []

    # Personality read → light tone prior, built from the constrained dimensions
    # (NOT a hard archetype block). It only tints HOW replies are phrased; the
    # direction/stage/tone rules drive WHAT the move is.
    # Phase 4: prefer the mode-smoothed dimensions (stable across scans) once
    # enough history exists; fall back per-dimension to the live scan otherwise.
    _stable_dims = (conversation_context or {}).get("stable_dimensions") or {}

    def _dim(name: str, default: str) -> str:
        return (
            _stable_dims.get(name)
            or getattr(analysis, name, default)
            or default
        )

    personality_prior = build_tone_prior(
        _dim("warmth", "neutral"),
        _dim("playfulness", "balanced"),
        _dim("engagement", "medium"),
        _dim("traditionalism", "mixed"),
        _dim("intent", "open"),
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
            "Do NOT just regenerate from scratch — improve the flagged replies.\n\n"
            f"{auditor_feedback}"
        )

    # --- Build conditional prompt (situational policy drives; personality tints) ---
    detected_dialect = getattr(analysis, "detected_dialect", "ENGLISH") or "ENGLISH"
    their_tone = getattr(analysis, "their_tone", "neutral") or "neutral"
    their_effort = getattr(analysis, "their_effort", "medium") or "medium"
    system_prompt = _build_generator_prompt(
        direction=direction,
        custom_hint=custom_hint,
        detected_dialect=str(detected_dialect),
        stage=stage,
        conversation_temperature=conversation_temperature,
        their_tone=str(their_tone),
        their_effort=str(their_effort),
        preferred_strategies=preferred_strategies if isinstance(preferred_strategies, list) else [],
        personality_prior=personality_prior,
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
                        {"text": r.text, "strategy_label": r.strategy_label, "is_recommended": r.is_recommended}
                        for r in gen_out.replies
                    ],
                    shadow_provider="groq",
                    shadow_model=settings.groq_model,
                    shadow_replies=[
                        {"text": r.text, "strategy_label": r.strategy_label, "is_recommended": r.is_recommended}
                        for r in shadow_out.replies
                    ],
                )
            except Exception:
                logger.warning("v2_generator_ab_shadow_failed", trace_id=trace_id, exc_info=True)

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
