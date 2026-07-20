"""Deterministic name anonymization for the video pipeline.

Ensures real person names never appear in rendered videos or filenames.
Returns only the first character of the real name (e.g. "A" for "Alex").
Unknown/sentinel names produce "M" (Match).
"""


def anonymize_name(real_name: str | None) -> str:
    """Return the first character of *real_name* as a pseudonym.

    Parameters
    ----------
    real_name:
        The actual person name from the database.  ``None``, empty, and
        sentinel values (``"unknown"``, ``"someone"``) all produce ``"M"``.
    """
    if not real_name:
        return "M"
    stripped = real_name.strip()
    if not stripped or stripped.lower() in ("unknown", "someone"):
        return "M"
    return stripped[0].upper()
