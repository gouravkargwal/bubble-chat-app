"""Dynamic temperature calculation based on direction × conversation state."""

# Matrix: direction → {conversation_temperature → llm_temperature}
_TEMP_MATRIX: dict[str, dict[str, float]] = {
    "quick_reply": {"cold": 0.65, "lukewarm": 0.70, "warm": 0.75, "hot": 0.80},
    "get_number": {"cold": 0.60, "lukewarm": 0.65, "warm": 0.70, "hot": 0.75},
    "ask_out": {"cold": 0.60, "lukewarm": 0.65, "warm": 0.70, "hot": 0.75},
    "keep_playful": {"cold": 0.75, "lukewarm": 0.80, "warm": 0.85, "hot": 0.85},
    "go_deeper": {"cold": 0.60, "lukewarm": 0.65, "warm": 0.70, "hot": 0.70},
    "change_topic": {"cold": 0.70, "lukewarm": 0.75, "warm": 0.80, "hot": 0.80},
}


def calculate_temperature(
    direction: str,
    conversation_temperature: str = "warm",
    stage: str = "early_talking",
    interaction_count: int = 0,
) -> float:
    """Calculate the optimal LLM temperature for this specific context."""
    direction_temps = _TEMP_MATRIX.get(direction, _TEMP_MATRIX["quick_reply"])
    base = direction_temps.get(conversation_temperature, 0.70)

    # Vulnerable/argument → clamp down for careful, measured output
    if stage == "vulnerable":
        base = min(base, 0.65)
    elif stage == "argument":
        base = min(base, 0.60)

    # First interaction → slightly more creative for openers
    if interaction_count == 0:
        base += 0.05

    # Clamp to safe range
    return max(0.50, min(base, 0.85))
