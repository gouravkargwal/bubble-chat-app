"""
Multi-turn scenario eval — run a full simulated S conversation through the
PRODUCTION Gemini generator path (real GeneratorOutput schema), turn by turn,
and print the recommended reply (★) + the 3 alternates with word counts.

Unlike eval_models.py (single payload, one direction), this walks a realistic
arc: opener → tease → keep_playful → go_deeper → ask_out. Use it to see whether
the brevity / anti-AI prompt rules hold as the conversation evolves.

Run inside the container:
  docker compose exec api python scripts/eval_scenario.py
  docker compose exec api python scripts/eval_scenario.py --temperature 0.9
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage, SystemMessage

from eval_models import build_system_prompt  # reuses prod _build_generator_prompt

from agent.nodes_v2._generator import GeneratorOutput
from agent.nodes_v2._lc_usage import invoke_structured_gemini
from app.config import settings

PROFILE = (
    "S 25\nLanguages\nHindi\nEnglish\nBasics\nSingle\nCapricorn\n5'3\"\nHindu\n"
    "Lucknow, Uttar Pradesh, IN\nNever\nSometimes\nNon-Vegetarian\nSometimes\n"
    "Active today\nRelationship goals\nLong-term relationship"
)

# P3 dossier: durable facts the coach already "knows" about her from past chats.
# Injected on returning turns (interaction_count > 0) so the run exercises whether
# the generator USES known facts and avoids re-asking what it already knows.
CORE_LORE = (
    "lives in Lucknow, Uttar Pradesh\n"
    "Capricorn\n"
    "Hindu\n"
    "looking for a long-term relationship"
)

# A coherent arc. `sent` = the reply we assume was chosen last turn (for narration
# + transcript continuity); `her_reply` = how she responds, advancing the chat.
TURNS = [
    {
        "title": "TURN 1 — OPENER (her profile only, first message)",
        "direction": "opener",
        "their_tone": "Reserved and traditional",
        "their_effort": "low",
        "conversation_temperature": "warm",
        "stage": "opening",
        "interaction_count": 0,
        "top_hooks": [],
        "transcript": [("them", PROFILE)],
        "their_last_message": "Sparse traditional profile: Capricorn, Hindu, Lucknow, long-term goals.",
        "user_last_move": "",
        "opener_hook_priority": "text_first",
        "her_reply": "haha kebab obviously, biryani is overrated tbh",
    },
    {
        "title": "TURN 2 — TEASE (she pushed back on biryani)",
        "direction": "tease",
        "their_tone": "warming, playful",
        "their_effort": "medium",
        "conversation_temperature": "warm",
        "stage": "early_talking",
        "interaction_count": 1,
        "top_hooks": ["biryani is overrated", "kebab obviously"],
        "transcript": [
            ("them", PROFILE),
            ("user", "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya"),
            ("them", "haha kebab obviously, biryani is overrated tbh"),
        ],
        "their_last_message": "Said kebab obviously and called biryani overrated — playful pushback.",
        "user_last_move": "Sent a playful opener about biryani vs kebabs in Lucknow.",
        "her_reply": "arre nahi tunday ke kebab try karke dekho phir baat karna",
    },
    {
        "title": "TURN 3 — KEEP PLAYFUL (she named a specific spot, invested)",
        "direction": "keep_playful",
        "their_tone": "engaged, teasing",
        "their_effort": "medium",
        "conversation_temperature": "warm",
        "stage": "early_talking",
        "interaction_count": 2,
        "top_hooks": ["tunday ke kebab", "try karke dekho phir baat karna"],
        "transcript": [
            ("them", PROFILE),
            ("user", "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya"),
            ("them", "haha kebab obviously, biryani is overrated tbh"),
            ("user", "biryani overrated bol diya, ab toh proof chahiye"),
            ("them", "arre nahi tunday ke kebab try karke dekho phir baat karna"),
        ],
        "their_last_message": "Doubled down, told him to try Tunday kebabs then talk.",
        "user_last_move": "Teased her 'biryani overrated' claim and asked for proof.",
        "her_reply": "waise aaj office mein bohot lamba din tha, thak gayi hu",
    },
    {
        "title": "TURN 4 — GO DEEPER (she shared something real)",
        "direction": "go_deeper",
        "their_tone": "a little low, tired, opening up",
        "their_effort": "medium",
        "conversation_temperature": "warm",
        "stage": "early_talking",
        "interaction_count": 3,
        "top_hooks": ["office mein lamba din", "thak gayi hu"],
        "transcript": [
            ("them", PROFILE),
            ("user", "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya"),
            ("them", "haha kebab obviously, biryani is overrated tbh"),
            ("user", "biryani overrated bol diya, ab toh proof chahiye"),
            ("them", "arre nahi tunday ke kebab try karke dekho phir baat karna"),
            ("user", "deal, par tum guide banogi warna main galat jagah kha aaunga"),
            ("them", "waise aaj office mein bohot lamba din tha, thak gayi hu"),
        ],
        "their_last_message": "Opened up that she had a long tiring day at the office and feels drained.",
        "user_last_move": "Agreed to the kebab plan and asked her to be his guide.",
        "her_reply": "haan thoda better, baat karke acha laga",
    },
    {
        "title": "TURN 5 — ASK OUT (warm, established, comfortable)",
        "direction": "ask_out",
        "their_tone": "warm, comfortable",
        "their_effort": "high",
        "conversation_temperature": "hot",
        "stage": "warming",
        "interaction_count": 4,
        "top_hooks": ["baat karke acha laga", "tunday ke kebab"],
        "transcript": [
            ("them", PROFILE),
            ("user", "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya"),
            ("them", "haha kebab obviously, biryani is overrated tbh"),
            ("user", "biryani overrated bol diya, ab toh proof chahiye"),
            ("them", "arre nahi tunday ke kebab try karke dekho phir baat karna"),
            ("user", "deal, par tum guide banogi warna main galat jagah kha aaunga"),
            ("them", "waise aaj office mein bohot lamba din tha, thak gayi hu"),
            ("user", "lamba din tha toh kebab break to banta hai"),
            ("them", "haan thoda better, baat karke acha laga"),
        ],
        "their_last_message": "Said she feels a bit better and enjoyed talking to him.",
        "user_last_move": "Reframed her tiring day as a reason to take a kebab break.",
    },
]


def _visual_transcript(turns):
    return [
        {"sender": s, "quoted_context": "", "actual_new_message": m} for s, m in turns
    ]


def _transcript_text(turns):
    return "\n".join(f"{s}: {m}" for s, m in turns)


def build_payload(turn: dict) -> dict:
    analysis = {
        "visual_transcript": _visual_transcript(turn["transcript"]),
        "visual_hooks": [
            "pink ruched mini dress",
            "traditional Indian attire with heavy bangles and maang tikka",
            "black sleeveless top with gold chain necklace",
        ],
        "photo_persona": "girl-next-door",
        "detected_dialect": "HINGLISH",
        "their_tone": turn["their_tone"],
        "their_effort": turn["their_effort"],
        "conversation_temperature": turn["conversation_temperature"],
        "warmth": "neutral",
        "playfulness": "earnest",
        "engagement": turn["their_effort"],
        "traditionalism": "traditional",
        "intent": "long_term",
        "detected_archetype": "THE TRADITIONAL ROMANTIC",
        "top_hooks": turn["top_hooks"],
        "key_detail": "Capricorn, Hindu, Lucknow, looking for a long-term relationship.",
        "person_name": "S",
        "stage": turn["stage"],
        "their_last_message": turn["their_last_message"],
        "user_last_move": turn["user_last_move"],
        "inbound_image": "none",
        "inbound_image_detail": "",
    }
    payload = {
        "analysis": analysis,
        "direction": turn["direction"],
        "person_name": "S",
        "core_lore": (CORE_LORE if turn["interaction_count"] > 0 else ""),
        "past_memories": "",
        "transcript_text": _transcript_text(turn["transcript"]),
        "voice_dna_dict": {},
        "conversation_context_dict": {
            "person_name": "S",
            "stage": turn["stage"],
            "tone_trend": "warming",
            "topics_worked": [],
            "topics_failed": [],
            "interaction_count": turn["interaction_count"],
            "recent_summaries": [],
            "recent_user_replies": [],
            "stable_archetype": None,
            "archetype_confidence": 0.0,
            "stable_dimensions": None,
            "photo_persona": "girl-next-door",
            "preferred_strategies": [],
        },
        "user_custom_hint": "",
    }
    if "opener_hook_priority" in turn:
        payload["opener_hook_priority"] = turn["opener_hook_priority"]
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--temperature", type=float, default=0.85)
    args = ap.parse_args()

    for turn in TURNS:
        payload = build_payload(turn)
        system_prompt = build_system_prompt(payload)
        human = json.dumps(payload)
        msgs = [SystemMessage(content=system_prompt), HumanMessage(content=human)]

        print("\n" + "=" * 92)
        print(turn["title"] + f"   [direction={turn['direction']}]")
        if turn["transcript"][-1][0] == "them" and turn["interaction_count"] > 0:
            print(f'  she just said: "{turn["transcript"][-1][1]}"')
        print("=" * 92)

        try:
            out, _ = invoke_structured_gemini(
                model=settings.gemini_model,
                temperature=args.temperature,
                schema=GeneratorOutput,
                messages=msgs,
                phase="eval_scenario",
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {type(exc).__name__}: {exc}")
            continue

        print(f"  strategy: {out.recommended_strategy_label}")
        for r in out.replies:
            star = "★" if r.is_recommended else " "
            wc = len(r.text.split())
            print(f"  {star} ({wc:>2}w) [{r.strategy_label}] {r.text}")

        if turn.get("her_reply"):
            print(f'  → (she replies next: "{turn["her_reply"]}")')


if __name__ == "__main__":
    main()
