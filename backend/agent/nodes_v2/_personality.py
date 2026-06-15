"""
Personality model for the v2 pipeline.

Instead of the LLM picking one archetype label from a fixed list (which it kept
hallucinating new names for, and which forced a static personality onto a dynamic
conversation), the vision node scores a few CONSTRAINED dimensions. These can't
hallucinate (each is a Literal) and there's no taxonomy to maintain — any person
is just a point in this space.

The dimensions feed two things:
  * derive_archetype(): a single derived label, kept ONLY for logging + the
    Phase 4/5 learning stats. It no longer drives the generator's tactics.
  * build_tone_prior(): a compact tone tint injected into the generator. It is
    explicitly subordinate to the situational rules (direction × stage × her
    current tone) — personality adjusts HOW you say it, never WHAT the move is.
"""

from __future__ import annotations

from typing import Literal

# Constrained personality axes. Defaults are the neutral midpoint so a missing
# value (e.g. an old cached vision_out) degrades to "let the situation lead".
Warmth = Literal["guarded", "neutral", "warm"]
Playfulness = Literal["earnest", "balanced", "playful"]
Engagement = Literal["low", "medium", "high"]
Traditionalism = Literal["modern", "mixed", "traditional"]
Intent = Literal["exploring", "open", "long_term"]


def derive_archetype(
    warmth: str,
    playfulness: str,
    engagement: str,
    traditionalism: str,
    intent: str,
) -> str:
    """Map a dimension vector to one of the known archetype labels.

    Priority-ordered: the most strategy-defining signal wins. This is a derived
    label for analytics/learning continuity only — the generator no longer uses
    it to select tactics.
    """
    if traditionalism == "traditional" and intent == "long_term":
        return "THE TRADITIONAL ROMANTIC"
    if traditionalism == "traditional":
        return "THE TRADITIONALIST"
    if warmth == "guarded":
        return "THE GUARDED/TESTER"
    if engagement == "low":
        return "THE LOW-INVESTMENT"
    if playfulness == "playful":
        return "THE BANTER GIRL"
    if playfulness == "earnest" and engagement == "high":
        return "THE INTELLECTUAL"
    if engagement == "high":
        return "THE EAGER/DIRECT"
    return "THE WARM/STEADY"


# Per-value tone guidance. Only NON-default values contribute a line, so the
# prior stays short and only mentions what's actually salient about her.
_TONE_HINTS: dict[str, dict[str, str]] = {
    "warmth": {
        "guarded": "she has walls up — earn engagement, stay unbothered, don't over-invest or try-hard",
        "warm": "she's receptive — you can be direct and friendly without hedging",
    },
    "playfulness": {
        "playful": "teasing and banter land — lighter, cockier phrasing is welcome",
        "earnest": "she's sincere — match with genuine curiosity; go easy on sarcasm",
    },
    "engagement": {
        "high": "she's investing real effort — you can match her energy",
        "low": "low investment — stay concise and high-value, do NOT chase or over-explain",
    },
    "traditionalism": {
        "traditional": "grounded/respectful presentation — avoid crude or edgy phrasing; don't make her background the joke",
        "modern": "casual/modern vibe — relaxed phrasing is fine",
    },
    "intent": {
        "long_term": "serious about relationship goals — do not joke about or tease her commitment intent",
        "exploring": "still figuring out what she wants — don't project seriousness onto her",
    },
}


def build_tone_prior(
    warmth: str,
    playfulness: str,
    engagement: str,
    traditionalism: str,
    intent: str,
) -> str:
    """Build a compact, situational-subordinate tone tint from the dimensions.

    Returns "" when every axis is neutral (let the situation lead entirely).
    """
    pairs = (
        ("warmth", warmth),
        ("playfulness", playfulness),
        ("engagement", engagement),
        ("traditionalism", traditionalism),
        ("intent", intent),
    )
    bullets: list[str] = []
    for axis, value in pairs:
        hint = _TONE_HINTS.get(axis, {}).get((value or "").strip().lower())
        if hint:
            bullets.append(f"* {hint}")

    if not bullets:
        return (
            "PERSONALITY READ: she reads as balanced — let the situational rules "
            "(direction, stage, her current tone) lead entirely.\n"
        )

    return (
        "PERSONALITY READ (tone prior ONLY — this adjusts HOW you phrase things, "
        "never WHAT the move is. The direction, stage, and her current emotional "
        "tone above ALWAYS override this. If the moment calls for something else, "
        "follow the moment):\n" + "\n".join(bullets) + "\n"
    )
