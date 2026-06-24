"""
Prompt Logger Script — Generates and logs the exact fully rendered system
and user prompts for each turn of the conversation scenario.

Use this to grab the exact text payload and test it raw in any LLM web UI,
playground, or chat terminal.

Run locally:
  python scripts/log_final_prompts.py
"""

from __future__ import annotations

import json
import os
import sys

# Configure environment path structures for clean execution
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, script_dir)

# Prompt template moved to app/prompts/scripts.py
from app.prompts.scripts import STREAMLINED_SYSTEM_PROMPT_TEMPLATE

PROFILE = (
    "S 25\nLanguages\nHindi\nEnglish\nBasics\nSingle\nCapricorn\n5'3\"\nHindu\n"
    "Lucknow, Uttar Pradesh, IN\nNever\nSometimes\nNon-Vegetarian\nSometimes\n"
    "Active today\nRelationship goals\nLong-term relationship"
)

CORE_LORE = (
    "lives in Lucknow, Uttar Pradesh\n"
    "Capricorn\n"
    "Hindu\n"
    "looking for a long-term relationship"
)

TURNS = [
    {
        "title": "TURN 1 — OPENER",
        "direction": "opener",
        "transcript": [("them", PROFILE)],
    },
    {
        "title": "TURN 2 — TEASE",
        "direction": "tease",
        "transcript": [
            ("them", PROFILE),
            (
                "user",
                "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya",
            ),
            ("them", "haha kebab obviously, biryani is overrated tbh"),
        ],
    },
    {
        "title": "TURN 3 — KEEP PLAYFUL",
        "direction": "keep_playful",
        "transcript": [
            ("them", PROFILE),
            (
                "user",
                "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya",
            ),
            ("them", "haha kebab obviously, biryani is overrated tbh"),
            ("user", "biryani overrated bol diya, ab toh proof chahiye"),
            ("them", "arre nahi tunday ke kebab try karke dekho phir baat karna"),
        ],
    },
    {
        "title": "TURN 4 — GO DEEPER",
        "direction": "go_deeper",
        "transcript": [
            ("them", PROFILE),
            (
                "user",
                "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya",
            ),
            ("them", "haha kebab obviously, biryani is overrated tbh"),
            ("user", "biryani overrated bol diya, ab toh proof chahiye"),
            ("them", "arre nahi tunday ke kebab try karke dekho phir baat karna"),
            ("user", "deal, par tum guide banogi warna main galat jagah kha aaunga"),
            ("them", "waise aaj office mein bohot lamba din tha, thak gayi hu"),
        ],
    },
]


def _transcript_text(turns):
    return "\n".join(f"{s}: {m}" for s, m in turns)


def main() -> None:
    print("\n" + "=" * 40)
    print("PROMPT INJECTION EXTRACTION ENGINE")
    print("=" * 40)

    for i, turn in enumerate(TURNS, start=1):
        transcript_str = _transcript_text(turn["transcript"])

        # Build the system instruction payload raw string
        rendered_system_prompt = STREAMLINED_SYSTEM_PROMPT_TEMPLATE.format(
            person_name="S",
            direction=turn["direction"],
            detected_dialect="HINGLISH",
            transcript_text=transcript_str,
        )

        # Build the user schema structured input text block
        mock_user_payload = {
            "analysis": {
                "detected_dialect": "HINGLISH",
                "person_name": "S",
                "visual_hooks": ["pink ruched mini dress"],
            },
            "direction": turn["direction"],
            "person_name": "S",
            "transcript_text": transcript_str,
        }
        rendered_user_payload = json.dumps(mock_user_payload, indent=2)

        # Output clean print segments block
        print(
            f"\n\n### [ROUND {i}] {turn['title']} [direction={turn['direction']}] ###"
        )
        print("-" * 92)
        print("--- RENDERED SYSTEM PROMPT CONTENT ---")
        print(rendered_system_prompt.strip())
        print("-" * 92)
        print("--- RENDERED USER PAYLOAD CONTENT ---")
        print(rendered_user_payload)
        print("=" * 92)


if __name__ == "__main__":
    main()
