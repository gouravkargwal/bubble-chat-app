"""Test LLM response parsing."""

import json

import pytest

from app.llm.response_parser import parse_llm_response


def test_parse_valid_json():
    """Should parse a well-formed JSON response."""
    response = json.dumps({
        "analysis": {
            "their_last_message": "just got back from a hike",
            "who_texted_last": "them",
            "their_tone": "playful",
            "their_effort": "medium",
            "conversation_temperature": "warm",
            "stage": "early_talking",
            "person_name": "Sarah",
            "key_detail": "hiking",
            "what_they_want": "banter",
        },
        "strategy": {
            "wrong_moves": ["being generic", "asking boring questions"],
            "right_energy": "playful and curious",
            "hook_point": "the hike",
        },
        "replies": [
            "your legs are dead but the views were worth it right",
            "okay but did you take the hard trail just to flex",
            "rip your legs... recovery plan is couch and netflix yeah",
            "you seem like someone who says almost there for the last hour",
        ],
    })

    parsed = parse_llm_response(response)
    assert len(parsed.replies) == 4
    assert parsed.analysis.person_name == "Sarah"
    assert parsed.analysis.stage == "early_talking"
    assert parsed.strategy.hook_point == "the hike"


def test_parse_json_in_code_block():
    """Should extract JSON from markdown code fences."""
    response = """Here are the replies:

```json
{
  "analysis": {"person_name": "Priya", "stage": "new_match"},
  "strategy": {"wrong_moves": [], "right_energy": "curious"},
  "replies": ["reply one", "reply two", "reply three", "reply four"]
}
```"""

    parsed = parse_llm_response(response)
    assert len(parsed.replies) == 4
    assert parsed.analysis.person_name == "Priya"


def test_parse_delimiter_format():
    """Should fall back to ---/=== delimiter format."""
    response = """okay but your dog is clearly the star
---
ngl your profile made me want to visit that cafe
---
you seem like the type who has strong opinions about coffee
---
wait is that a golden retriever or are my eyes lying
===
CONTEXT: Person name: Aisha. Early conversation about her dog and a cafe. Stage: early_talking."""

    parsed = parse_llm_response(response)
    assert len(parsed.replies) == 4
    assert parsed.analysis.person_name == "Aisha"


def test_parse_strips_reply_labels():
    """Should remove numbered prefixes from replies."""
    response = json.dumps({
        "analysis": {"person_name": "unknown"},
        "strategy": {},
        "replies": [
            "1. first reply here",
            "Reply 2: second reply",
            "Flirty: third reply text",
            "4) fourth reply text",
        ],
    })

    parsed = parse_llm_response(response)
    assert not parsed.replies[0].startswith("1.")
    assert "Reply 2:" not in parsed.replies[1]


def test_parse_error_response():
    """Should raise on UNREADABLE error."""
    response = json.dumps({"error": "UNREADABLE"})
    with pytest.raises(ValueError, match="UNREADABLE"):
        parse_llm_response(response)


def test_parse_garbage_raises():
    """Should raise on completely unparseable input."""
    with pytest.raises(ValueError):
        parse_llm_response("this is just random text with no structure")
