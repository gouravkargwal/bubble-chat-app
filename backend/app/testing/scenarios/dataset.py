"""Test scenario loader and validator."""

import json
from pathlib import Path

from pydantic import BaseModel


class QualityCriteria(BaseModel):
    must_reference: list[str] = []
    must_have_fork: bool = True


class Scenario(BaseModel):
    id: str
    category: str
    description: str
    their_last_message: str  # what she said last (empty for new_match with no messages)
    person_name: str = "unknown"
    direction: str
    expected_stage: str
    expected_tone: str
    quality_criteria: QualityCriteria


_SCENARIOS_PATH = Path(__file__).parent / "scenarios.json"
_cache: list[Scenario] | None = None


def get_all() -> list[Scenario]:
    """Load and validate all test scenarios."""
    global _cache
    if _cache is not None:
        return _cache

    raw = json.loads(_SCENARIOS_PATH.read_text())
    _cache = [Scenario(**s) for s in raw]
    return _cache


def get_by_category(category: str) -> list[Scenario]:
    return [s for s in get_all() if s.category == category]


def get_by_id(scenario_id: str) -> Scenario | None:
    return next((s for s in get_all() if s.id == scenario_id), None)


def get_categories() -> list[str]:
    return sorted(set(s.category for s in get_all()))


# ---------------------------------------------------------------------------
# Mock AnalystOutput builder — converts scenario metadata into the structured
# context that generator_node + auditor_node expect.
# Skips the vision/OCR node entirely — that's what we want for prompt eval.
# ---------------------------------------------------------------------------

_TONE_TO_ARCHETYPE: dict[str, str] = {
    "sarcastic": "THE BANTER GIRL",
    "testing": "THE GUARDED/TESTER",
    "playful": "THE BANTER GIRL",
    "excited": "THE EAGER/DIRECT",
    "flirty": "THE EAGER/DIRECT",
    "dry": "THE LOW-INVESTMENT",
    "neutral": "THE WARM/STEADY",
    "upset": "THE WARM/STEADY",
    "vulnerable": "THE WARM/STEADY",
}

_CATEGORY_TO_TEMPERATURE: dict[str, str] = {
    "new_match": "lukewarm",
    "early_conversation": "warm",
    "building_chemistry": "warm",
    "dying_conversation": "cold",
    "testing": "warm",
    "vulnerable": "warm",
    "goal_oriented": "warm",
    "relationship": "hot",
}

_CATEGORY_TO_EFFORT: dict[str, str] = {
    "dying_conversation": "low",
    "testing": "medium",
    "vulnerable": "high",
    "relationship": "high",
}


def build_analyst_output(scenario: Scenario) -> dict:
    """
    Build a mock AnalystOutput dict for generator_node + auditor_node.

    Uses scenario fields directly — no regex parsing needed.
    """
    archetype = _TONE_TO_ARCHETYPE.get(scenario.expected_tone, "THE WARM/STEADY")
    temperature = _CATEGORY_TO_TEMPERATURE.get(scenario.category, "warm")
    effort = _CATEGORY_TO_EFFORT.get(scenario.category, "medium")

    hooks = scenario.quality_criteria.must_reference[:3]
    key_detail = hooks[0] if hooks else scenario.description[:60]

    visual_transcript = []
    if scenario.their_last_message:
        visual_transcript.append(
            {
                "sender": "them",
                "quoted_context": "",
                "actual_new_message": scenario.their_last_message,
            }
        )

    return {
        "visual_transcript": visual_transcript,
        "visual_hooks": [],
        "detected_dialect": "ENGLISH",
        "their_tone": scenario.expected_tone,
        "their_effort": effort,
        "conversation_temperature": temperature,
        "archetype_reasoning": (
            f"Based on tone '{scenario.expected_tone}' and category '{scenario.category}', "
            f"classified as {archetype}."
        ),
        "detected_archetype": archetype,
        "top_hooks": hooks,
        "key_detail": key_detail,
        "person_name": scenario.person_name,
        "stage": scenario.expected_stage,
        "their_last_message": scenario.their_last_message or scenario.description,
    }
