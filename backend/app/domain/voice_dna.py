"""Voice DNA — learns user's texting style from copied replies."""

import json
import re

from app.domain.models import VoiceDNA
from app.infrastructure.database.models import UserVoiceDNA

# Common slang/abbreviations to track
_SLANG_WORDS = {
    "lol", "haha", "hahaha", "lmao", "ngl", "tbh", "lowkey", "fr", "imo",
    "omg", "bruh", "gonna", "wanna", "kinda", "tho", "nah", "idk", "imo",
    "ikr", "smh", "istg", "rn", "bro", "dude", "yoo", "yooo", "bet",
}


def update_from_copy(current: UserVoiceDNA, copied_text: str) -> UserVoiceDNA:
    """Update Voice DNA running averages from a newly copied reply."""
    n = current.sample_count
    new_n = n + 1

    # Running average: reply length (characters)
    current.avg_reply_length = (current.avg_reply_length * n + len(copied_text)) / new_n

    # Emoji count
    emoji_count = len(re.findall(r"[\U0001f600-\U0001f9ff\U0001fa00-\U0001faff\u2600-\u26ff\u2700-\u27bf]", copied_text))
    current.emoji_count += emoji_count
    current.emoji_frequency = current.emoji_count / new_n

    # Capitalization
    is_lowercase = copied_text == copied_text.lower()
    current.lowercase_count += 1 if is_lowercase else 0
    current.capitalization = "lowercase" if current.lowercase_count / new_n > 0.7 else "normal"

    # Punctuation
    has_ellipsis = "..." in copied_text
    has_no_period = not copied_text.rstrip().endswith(".")
    current.ellipsis_count += 1 if has_ellipsis else 0
    current.no_period_count += 1 if has_no_period else 0

    if current.ellipsis_count / new_n > 0.3:
        current.punctuation_style = "ellipsis lover"
    elif current.no_period_count / new_n > 0.7:
        current.punctuation_style = "no periods"
    else:
        current.punctuation_style = "casual"

    # Word frequency tracking
    word_freq = json.loads(current.word_frequency) if current.word_frequency else {}
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


def to_domain(db_model: UserVoiceDNA) -> VoiceDNA:
    """Convert DB model to domain model for prompt injection."""
    common = json.loads(db_model.common_words) if db_model.common_words else []
    return VoiceDNA(
        avg_reply_length=db_model.avg_reply_length,
        emoji_frequency=db_model.emoji_frequency,
        common_words=common if isinstance(common, list) else [],
        punctuation_style=db_model.punctuation_style,
        capitalization=db_model.capitalization,
        preferred_length=db_model.preferred_length,
        sample_count=db_model.sample_count,
    )
