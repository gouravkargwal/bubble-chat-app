"""Test scenario loader and validator."""

import json
from pathlib import Path

from pydantic import BaseModel


class QualityCriteria(BaseModel):
    must_reference: list[str] = []
    forbidden_patterns: list[str] = []
    max_length_chars: int = 200
    must_have_fork: bool = True
    must_not_ask_question: bool = False


class Scenario(BaseModel):
    id: str
    category: str
    description: str
    screenshot_description: str
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
