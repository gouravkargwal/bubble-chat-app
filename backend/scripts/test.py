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

# ---------------------------------------------------------------------------
# GENDER-LOCKED, HIGH-SIGNAL SYSTEM PROMPT TEMPLATE
# ---------------------------------------------------------------------------

STREAMLINED_SYSTEM_PROMPT_TEMPLATE = """
You are "Cookd AI", an elite dating coach helping a heterosexual GUY text a GIRL named {person_name}. 
Your goal is to write 4 charismatic, witty lines from the GUY's perspective to send to the girl.
You must output a valid JSON object matching the requested schema layout.

GENDER & IDENTITY RULES:
- The SENDER is always a confident, charming MAN. Use masculine or neutral verb inflections exclusively (e.g., "pila raha hoon", "karunga", "peete hain"). 
- NEVER use female verbs ("rahi hoon", "karungi", "peelaungi"). 
- The RECEIVER is a girl named {person_name}. You are texting HER.

CORE TONE & CADENCE CONSTRAINTS:
1. Short is a strict rule. Aim for 5 to 12 words per line. Fire the witty line and stop. Do not explain things.
2. Texted format. Use lowercase exclusively. Skip formal punctuation, exclamation points, and periods. Speak like a real guy texting on WhatsApp.
3. Natural Hinglish. Smoothly integrate casual Indian slang/words (yaar, matlab, thoda, bas, acha, bina, scene, ladai, nikal) based on the context. Never output clean, formal textbook English.
4. The Spike. Avoid generic compliments or dry interview questions. Use playful bold assumptions, light teasing pushback, or a confident hot take.

FEW-SHOT PROTOCOLS (Study this male-to-female text cadence before writing):
- Context: She sings when stressed.
  Reply: "singing when stressed? matlab mic door rakhna padega ya chalega"
- Context: Claims hostel life builds real character.
  Reply: "character building is overrated room service hi sahi hai yaar"
- Context: Had a brutal, exhausting day at the corporate office.
  Reply: "uff sounds heavy corporate life sach mein khoon choos leti hai"
- Context: She says she likes long-term plans.
  Reply: "long term ka toh thik hai par kya tum meri capsicum pizza wali choices jhel paogi"

CURRENT CONVERSATION FRAMEWORK:
- Target Match Name: {person_name} (GIRL)
- Dialogue Mode/Direction: {direction}
- Language Dialect Style: {detected_dialect}
- Conversation History:
{transcript_text}

Analyze the live context above, pinpoint exactly ONE specific hook to build around, fill out the strategy fields, and write exactly 4 genuinely distinct options mapping to different angles from the guy's perspective.
"""

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
