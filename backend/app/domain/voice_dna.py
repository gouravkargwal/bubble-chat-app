"""Voice DNA — learns user's texting style from copied replies."""

import difflib
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
    # Hindi/Hinglish slang
    "yaar",
    "bhai",
    "bro",
    "arre",
    "matlab",
    "toh",
    "kya",
    "acha",
    "haan",
    "nahi",
    "bilkul",
    "ekdum",
    "bas",
    "abhi",
    "thoda",
    "bahut",
    "chal",
    "kar",
    "tha",
    "hai",
    "hun",
    "karo",
    "mera",
    "tera",
    "apna",
    "kyun",
    "phir",
    "waise",
    "vaise",
    "scene",
    "sorted",
    "sahi",
}


def is_echo_text(candidate: str, past_replies: list[str]) -> bool:
    """Return True if candidate closely matches any of the past_replies (echo detection)."""
    candidate_norm = candidate.lower().strip()
    for past_reply in past_replies:
        reply_norm = past_reply.lower().strip()
        if len(reply_norm) < 6:
            continue
        if candidate_norm == reply_norm:
            return True
        if difflib.SequenceMatcher(None, candidate_norm, reply_norm).ratio() >= 0.85:
            return True
    return False


def update_voice_dna_stats(current: UserVoiceDNA, organic_text: str) -> UserVoiceDNA:
    """Update Voice DNA running averages from a newly observed organic reply."""
    # Older rows might have NULLs; treat them as zeros for running averages.
    n = current.sample_count or 0
    new_n = n + 1

    # Running average: reply length (characters)
    base_avg = current.avg_reply_length or 0.0
    current.avg_reply_length = (base_avg * n + len(organic_text)) / new_n

    # Emoji count
    emoji_count = len(
        re.findall(
            r"[\U0001f600-\U0001f9ff\U0001fa00-\U0001faff\u2600-\u26ff\u2700-\u27bf]",
            organic_text,
        )
    )
    current.emoji_count = (current.emoji_count or 0) + emoji_count
    current.emoji_frequency = current.emoji_count / new_n

    # Capitalization
    is_lowercase = organic_text == organic_text.lower()
    current.lowercase_count = (current.lowercase_count or 0) + (
        1 if is_lowercase else 0
    )
    lowercase_ratio = current.lowercase_count / new_n
    if lowercase_ratio > 0.7:
        current.capitalization = "lowercase"
    else:
        current.capitalization = "normal"

    # Punctuation
    has_ellipsis = "..." in organic_text
    has_no_period = not organic_text.rstrip().endswith(".")
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
            import structlog as _structlog
            _structlog.get_logger().warning(
                "voice_dna_word_frequency_corrupted",
                user_id=getattr(current, "user_id", "unknown"),
            )
    words = organic_text.lower().split()
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

    # Maintain rolling window of recent organic messages (last 5)
    try:
        recent_msgs = (
            json.loads(current.recent_organic_messages)
            if current.recent_organic_messages
            else []
        )
    except (json.JSONDecodeError, TypeError):
        import structlog as _structlog
        _structlog.get_logger().warning(
            "voice_dna_recent_messages_corrupted",
            user_id=getattr(current, "user_id", "unknown"),
        )
        recent_msgs = []

    recent_msgs.append(organic_text)
    recent_msgs = recent_msgs[-5:]
    current.recent_organic_messages = json.dumps(recent_msgs)

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
        recent_organic_messages=(
            json.loads(db_model.recent_organic_messages)
            if getattr(db_model, "recent_organic_messages", None)
            else []
        ),
    )
