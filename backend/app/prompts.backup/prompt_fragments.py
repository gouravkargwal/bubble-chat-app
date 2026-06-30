"""
Shared prompt fragments used across multiple prompt templates.

These fragments are injected into both the generator and auditor prompts
to keep them in sync. They serve as the single source of truth for:
- Strategy label definitions
- Banned example phrases (illustrative, not to be copied verbatim)
- AI-smell scaffold rules
"""

# Single source of truth for what each strategy_label MEANS. Injected into BOTH
# the generator (so it labels consistently) and the auditor (so it can catch
# mismatches). Consistency matters more than philosophical purity: Phase 5 learns
# "what works" keyed on strategy_label, so the SAME tactic must always get the
# SAME label or the learning signal is corrupted.
STRATEGY_LABEL_GLOSSARY = """STRATEGY LABEL DEFINITIONS (label each reply by what it ACTUALLY does — pick the dominant tactic):
* PUSH-PULL — gives and takes in one line: a compliment/acknowledgment immediately undercut by a tease or challenge. Litmus: it BOTH warms AND pokes. ("you seem fun but i bet you're trouble")
* FRAME CONTROL — you set or flip the frame: reinterpret her statement, define the terms, or assign roles. ALL "would you rather / A or B" hypotheticals go here (YOU set the choice). Litmus: you control the narrative or the choice, not her.
* VALUE ANCHOR — anchors on a specific real detail to build genuine connection; shows you actually noticed something concrete. Litmus: grounds in a real detail to CONNECT, not to tease.
* PATTERN INTERRUPT — an unexpected angle that breaks the predictable opener script. Litmus: she would NOT see it coming.
* HONEST FRAME — sincere and direct, no game: states something genuine or names something plainly. Litmus: earnest, zero tease, no tactic underneath.
* SOFT CLOSE — gently nudges momentum toward a next step (keep talking / meet) without a hard ask. Litmus: moves the interaction forward.
The strategy_label MUST match the litmus for the reply text. A question that makes her pick between two options = FRAME CONTROL, NOT HONEST FRAME. Pure validation/agreement is NOT a tactic — if a reply only validates, it is HONEST FRAME."""

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
