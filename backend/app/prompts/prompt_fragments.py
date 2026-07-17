"""
Shared prompt fragments used across multiple prompt templates.

These fragments are injected into both the generator and auditor prompts
to keep them in sync. They serve as the single source of truth for:
- Strategy label definitions
- Banned example phrases (illustrative, not to be copied verbatim)
- AI-smell scaffold rules
"""

# ---------------------------------------------------------------------------
# Scene direction mapping — translates raw API direction values into
# screenplay-style scene descriptions for the generator and auditor.
# Kept here so BOTH nodes see the same scene description for a given direction.
# ---------------------------------------------------------------------------

_DIRECTION_TO_SCENE: dict[str, str] = {
    "opener": (
        "SCENE: FIRST MEET — Kabir is writing his very first message to a girl "
        "he matched with. He has never spoken to her before. He ignores standard "
        "greetings ('hey', 'hi', 'hello') and instead opens with a sharp, playful "
        "observation from her profile — a photo detail, a bio line, or a prompt "
        "answer. The goal: make her want to reply instantly."
    ),
    "quick_reply": (
        "SCENE: BANTER RETURN — Kabir keeps the conversation flowing. He ignores "
        "low-effort tokens ('haha', 'lol', emojis) and rides her last actual "
        "message into a playful push, a bold assumption, or a fresh angle. The "
        "ball goes back to her court immediately."
    ),
    "keep_playful": (
        "SCENE: PLAYFUL RALLY — The vibe is light and banter-driven. Kabir extends "
        "the thread with pushback, a cocky misinterpretation, or a frame-flip. He "
        "does NOT close, ask out, or go serious — the scene stays in playful mode."
    ),
    "tease": (
        "SCENE: COCKY MISCHIEF — Kabir playfully challenges something she just said "
        "or did. He misinterprets her words on purpose, flips her frame, or calls "
        "out a contradiction with mock outrage. The tease is pointed at what she "
        "SAID, not who she IS — never a character verdict."
    ),
    "change_topic": (
        "SCENE: FRESH START — The current thread has run its course. Kabir pivots "
        "to a completely new angle — anchored to a specific profile detail or a "
        "fresh playful assumption. He does NOT meta-comment on the dead topic."
    ),
    "revive_chat": (
        "SCENE: WARM RE-ENGAGEMENT — The conversation has gone cold or stalled. "
        "Kabir reaches out light and easy, as if no time passed. This is NOT the "
        "moment for a cocky jab, a harsh tease, or an 'accusation' about her "
        "behaviour. Instead: a playful callback to something she shared, a warm "
        "fresh observation, or a self-aware pattern interrupt. The tone is "
        "FRIENDLY and LOW-INVESTMENT — make her smile, not brace herself. "
        "If a line could feel like an attack on her personality or choices, "
        "scrap it and go warmer. No neediness, no guilt, no edges that draw blood."
    ),
    "get_number": (
        "SCENE: MOVING OFF-APP — Kabir escalates the dynamic toward an off-app "
        "connection. At least 3 of 4 replies include an explicit ask anchored to "
        "something specific from the conversation. Platform choice (WhatsApp / "
        "Instagram / number) matches her warmth. Never puts a fake number in the reply."
    ),
    "ask_out": (
        "SCENE: DATE REQUEST — Kabir transitions from app chat to a real-life meeting. "
        "At least 2 of 4 replies include a concrete, conversation-anchored ask with "
        "a specific activity. Day specificity matches her conversation temperature. "
        "The ask feels like a natural next beat, not a formal request."
    ),
    "go_deeper": (
        "SCENE: EMOTIONAL BEAT — She shared something real or vulnerable. Kabir "
        "drops the banter and meets her there — raw, short, human. Each reply uses "
        "a different move: naming the thing, raw reaction, curious inner-experience "
        "question, or a gentle reframe. No advice, no pep talks, no redirecting."
    ),
    "de_escalate": (
        "SCENE: DE-ESCALATION — There is tension or a disagreement in the thread. "
        "Kabir stays grounded and owns specifics. No sarcasm, no dismissal. "
        "Each reply acknowledges the event first, then opens space forward."
    ),
}


def _resolve_scene_direction(direction: str) -> str:
    """Transform a raw API direction value into a screenplay-style scene description.

    Falls back to a generic scene label if the direction is unknown.
    Used by both the generator (screenwriter) and auditor (showrunner) so they
    are always looking at the same scene brief.
    """
    mapped = _DIRECTION_TO_SCENE.get(direction)
    if mapped:
        return mapped
    return (
        f"SCENE: {direction.replace('_', ' ').upper()} — "
        "Kabir responds in character, keeping the tone authentic to the moment."
    )


# ---------------------------------------------------------------------------
# Single source of truth for what each strategy_label MEANS. Injected into BOTH
# the generator (so it labels consistently) and the auditor (so it can catch
# mismatches). Consistency matters more than philosophical purity: Phase 5 learns
# "what works" keyed on strategy_label, so the SAME tactic must always get the
# SAME label or the learning signal is corrupted.
STRATEGY_LABEL_GLOSSARY = """STRATEGY LABEL DEFINITIONS (label each reply by what it ACTUALLY does — pick the dominant tactic):
* PUSH-PULL — gives and takes in one line: a compliment/acknowledgment immediately undercut by a tease or challenge. Litmus: it BOTH warms AND pokes. ("you seem fun but i bet you're trouble")
* FRAME CONTROL — you set or flip the frame: reinterpret her statement, define the terms, or assign roles. ALL "would you rather / A or B" hypotheticals go here (YOU set the choice). Litmus: you control the narrative or the choice, not her.
* VALUE ANCHOR — anchors on a specific real detail with unbothered, detached confidence; shows you actually noticed something concrete, without needing to challenge or undercut it. Can absolutely carry a playful or mischievous edge (e.g. in a tease scene) — what it does NOT do is the push-then-pull, warm-then-poke structure of PUSH-PULL. Litmus: grounds in a real detail and stays relaxed about it, no give-and-take.
* PATTERN INTERRUPT — an unexpected angle that breaks the predictable opener script. Litmus: she would NOT see it coming.
* HONEST FRAME — sincere and direct, no game: states something genuine or names something plainly. Litmus: earnest, zero tease, no tactic underneath.
* SOFT CLOSE — gently nudges momentum toward a next step (keep talking / meet) without a hard ask. Litmus: moves the interaction forward, but leaves the actual invite unstated.
* DIRECT ASK — makes an explicit, concrete ask: a specific day, activity, or platform (WhatsApp/Instagram/number), anchored to something real from the conversation. Litmus: it contains an actual proposal, not just an opening for one — this is what SOFT CLOSE stops short of.
The strategy_label MUST match the litmus for the reply text. A question that makes her pick between two options = FRAME CONTROL, NOT HONEST FRAME. Pure validation/agreement is NOT a tactic — if a reply only validates, it is HONEST FRAME. A concrete "let's do X on day Y" is DIRECT ASK, never SOFT CLOSE."""

# The illustrative example phrases baked into the prompts TEACH a technique —
# they are NOT lines to send. The generator has been observed copying them
# verbatim (e.g. "hits snooze 6 times"), producing generic replies ungrounded in
# HER profile. Treat these as banned strings in both the generator self-check and
# the auditor, the same way last_ai_replies_shown is treated for freshness.
BANNED_EXAMPLE_PHRASES = """BANNED EXAMPLE LINES (these phrases appear in your instructions only to ILLUSTRATE a technique — they are NOT content to send). NEVER reproduce any of them verbatim or near-verbatim; build the SAME technique from HER actual profile instead. A reply reusing one = automatic rewrite:
* "hits snooze 6 times" / "snooze 6 times" / "shows up with iced coffee"
* "i was going to say hi but then i saw your taste in music"
* "rot on the couch"
* "half marathon is just a biryani excuse"
* "goa as their answer to everything"
These are full canned SENTENCES. A single common word from one of them (biryani, goa, coffee, hiking, marathon, chai) is NOT banned on its own — only the specific sentence/construction is. e.g. "har weekend biryani khaogi?" is FINE; "the half marathon is just a biryani excuse" is NOT.
EXCEPTION: if HER profile genuinely contains the topic (she really mentions a half marathon, goa, etc.), you may reference the real detail — but never paste the canned phrasing."""

# Single source of truth for the AI-SMELL scaffold rule, shared by the generator
# (don't WRITE these) and the auditor (don't FAIL the allowed forms). Keeping it in
# one place stops the two from drifting — that drift is what made the auditor reject
# the generator's own allowed "are you the type who" jab. KEY: a scaffold is a SOFT
# OBSERVATIONAL OPENER; judge the OPENING WORDS, never the mere presence of "type who".
SCAFFOLD_RULE = """A SCAFFOLD is a SOFT OBSERVATIONAL OPENER — judge ONLY the reply's opening words. Banned openers: "you strike me as", any "you seem ..." ("you seem like the type", "you seem the type to", "you seem efficient"), "you look like ...", "i get the sense", "i suspect", "i need to know if", "there's something about you that", "i feel like you're the kind of person who", and balanced "either you X or you Y". The mere presence of "the type who/to" is NEVER itself a scaffold — the DIRECT forms are GOOD and wanted: "are you the type who [behavior]", "bet you [behavior]", a short "type who [behavior]" jab. Flip a soft opener to a direct jab ("you seem the type to over-plan" -> "bet you over-plan everything"). Do NOT generalize the ban beyond the openers listed (e.g. "you clearly", "i can tell", "sounds like you" are NOT scaffolds)."""
