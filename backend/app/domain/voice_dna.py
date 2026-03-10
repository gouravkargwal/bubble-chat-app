"""Voice DNA — learns user's texting style from copied replies."""

import json
import re

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import VoiceDNA
from app.infrastructure.database.models import UserVoiceDNA, Interaction

# Common slang/abbreviations to track
_SLANG_WORDS = {
    "lol",
    "haha",
    "hahaha",
    "lmao",
    "ngl",
    "tbh",
    "lowkey",
    "fr",
    "imo",
    "omg",
    "bruh",
    "gonna",
    "wanna",
    "kinda",
    "tho",
    "nah",
    "idk",
    "imo",
    "ikr",
    "smh",
    "istg",
    "rn",
    "bro",
    "dude",
    "yoo",
    "yooo",
    "bet",
}


def update_from_copy(current: UserVoiceDNA, copied_text: str) -> UserVoiceDNA:
    """Update Voice DNA running averages from a newly copied reply."""
    # Older rows might have NULLs; treat them as zeros for running averages.
    n = current.sample_count or 0
    new_n = n + 1

    # Running average: reply length (characters)
    base_avg = current.avg_reply_length or 0.0
    current.avg_reply_length = (base_avg * n + len(copied_text)) / new_n

    # Emoji count
    emoji_count = len(
        re.findall(
            r"[\U0001f600-\U0001f9ff\U0001fa00-\U0001faff\u2600-\u26ff\u2700-\u27bf]",
            copied_text,
        )
    )
    current.emoji_count = (current.emoji_count or 0) + emoji_count
    current.emoji_frequency = current.emoji_count / new_n

    # Capitalization
    is_lowercase = copied_text == copied_text.lower()
    current.lowercase_count = (current.lowercase_count or 0) + (
        1 if is_lowercase else 0
    )
    current.capitalization = (
        "lowercase" if current.lowercase_count / new_n > 0.7 else "normal"
    )

    # Punctuation
    has_ellipsis = "..." in copied_text
    has_no_period = not copied_text.rstrip().endswith(".")
    current.ellipsis_count = (current.ellipsis_count or 0) + (1 if has_ellipsis else 0)
    current.no_period_count = (current.no_period_count or 0) + (
        1 if has_no_period else 0
    )

    if current.ellipsis_count / new_n > 0.3:
        current.punctuation_style = "ellipsis lover"
    elif current.no_period_count / new_n > 0.7:
        current.punctuation_style = "no periods"
    else:
        current.punctuation_style = "casual"

    # Word frequency tracking (Bulletproof JSON parsing)
    word_freq: dict[str, int] = {}
    if current.word_frequency:
        try:
            parsed = json.loads(current.word_frequency)
            if isinstance(parsed, dict):
                word_freq = parsed
        except (json.JSONDecodeError, TypeError):
            # Fallback to empty dict if corrupted
            pass
    words = copied_text.lower().split()
    for word in words:
        clean = word.strip(".,!?\"'()[]")
        if clean in _SLANG_WORDS:
            word_freq[clean] = word_freq.get(clean, 0) + 1

    current.word_frequency = json.dumps(word_freq)

    # Top 5 common words
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    current.common_words = json.dumps([w for w, _ in sorted_words[:5]])

    # Preferred length bucket
    avg_word_count = current.avg_reply_length / 5  # rough chars-to-words
    if avg_word_count < 8:
        current.preferred_length = "short"
    elif avg_word_count > 20:
        current.preferred_length = "long"
    else:
        current.preferred_length = "medium"

    current.sample_count = new_n

    return current


async def to_domain(db_model: UserVoiceDNA, db: AsyncSession) -> VoiceDNA:
    """Convert DB model to domain model for prompt injection, including vibe preferences."""
    common = json.loads(db_model.common_words) if db_model.common_words else []

    # Calculate vibe preferences from user's ratings
    VIBE_NAMES = ["Flirty", "Witty", "Smooth", "Bold"]

    # Count all ratings (positive and negative) grouped by vibe index
    ratings_result = await db.execute(
        select(
            Interaction.rating_index,
            Interaction.rating_positive,
            func.count(Interaction.id).label("cnt"),
        )
        .where(
            Interaction.user_id == db_model.user_id,
            Interaction.rating_index.is_not(None),
        )
        .group_by(Interaction.rating_index, Interaction.rating_positive)
    )
    ratings_rows = ratings_result.all()

    # Calculate net score for each vibe: (positive_count - negative_count)
    vibe_scores = {}  # {vibe_index: net_score}
    for row in ratings_rows:
        vibe_idx = row.rating_index
        count = row.cnt
        if vibe_idx not in vibe_scores:
            vibe_scores[vibe_idx] = 0
        if row.rating_positive:
            vibe_scores[vibe_idx] += count
        else:
            vibe_scores[vibe_idx] -= count

    # Determine top vibes (positive net score) and disliked vibes (negative net score)
    top_vibes = []
    disliked_vibes = []

    for vibe_idx, score in vibe_scores.items():
        if 0 <= vibe_idx < len(VIBE_NAMES):
            vibe_name = VIBE_NAMES[vibe_idx]
            if score > 0:
                top_vibes.append((vibe_name, score))
            elif score < 0:
                disliked_vibes.append(vibe_name)

    # Sort top vibes by score descending and extract just the names
    top_vibes.sort(key=lambda x: x[1], reverse=True)
    top_vibe_names = [name for name, _ in top_vibes]

    return VoiceDNA(
        avg_reply_length=db_model.avg_reply_length,
        emoji_frequency=db_model.emoji_frequency,
        common_words=common if isinstance(common, list) else [],
        punctuation_style=db_model.punctuation_style,
        capitalization=db_model.capitalization,
        preferred_length=db_model.preferred_length,
        sample_count=db_model.sample_count,
        top_vibes=top_vibe_names,
        disliked_vibes=disliked_vibes,
    )
