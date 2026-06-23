"""
Multi-turn scenario eval (SCRIPTWRITER GEMINI EDITION) — runs a full simulated
conversation through the production Gemini generator path using the real
GeneratorOutput schema, overriding the prompt with the Netflix scriptwriter hack.

Run inside the container:
  docker compose exec api python scripts/eval_scenario_scriptwriter_gemini.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage, SystemMessage

from agent.nodes_v2._generator import GeneratorOutput
from agent.nodes_v2._lc_usage import invoke_structured_gemini
from app.config import settings

# ---------------------------------------------------------------------------
# PRODUCTION CINEMATIC SYSTEM PROMPT (THE FRONTIER MODEL HACK)
# ---------------------------------------------------------------------------

SCRIPTWRITER_GEMINI_PROMPT_TEMPLATE = """
You are an award-winning screenwriter for Netflix India, celebrated for writing hyper-realistic, sharp, and effortless modern dialogue for youth-centric web series (like 'Mismatched' or 'Panchayat'). 

You are currently writing an authentic texting scene between two characters:
- SENDER ("Kabir"): A confident, slightly detached, witty guy from an Indian metro city. He talks in relaxed, unbothered, lowercase sentences. He never uses emojis, exclamation points, or formal punctuation.
- RECEIVER ("{person_name}"): A girl he recently crossed paths with.

CRITICAL DIALECT & STYLE CONSTRAINTS:
1. Pure Contemporary Hinglish: Kabir speaks exactly how sharp, modern young adults text on WhatsApp. He organically mixes Romanized Hindi phrases (matlab, yaar, thoda, bas, acha, scene, vaise, ladai) without making them look forced or robotic. Never use stiff, formal, or textbook English.
2. Format Rules: Strictly lowercase text values for his dialogue. Skip formal punctuation, periods, and trailing filler. Keep lines short (5 to 12 words). Fire the spike and stop immediately—never explain the subtext or the joke.
3. The Spike: Every single option must carry an edge—a bold playful assumption, a deadpan challenge, or a confident hot take. Avoid nice-guy validation, clinical analytical statements, or generic compliments.

Your output must strictly adhere to the requested schema. Map your creative screenplay generation workflow directly into the fields like this:
- wrong_moves: 2-3 clinical, corny, or validation-heavy texting anti-patterns Kabir must avoid in this specific scene context.
- right_energy: A brief single phrase naming Kabir's current vibe/tone.
- hook_point: The specific detail from her message/profile Kabir is building his text around.
- recommended_strategy_label: The operational strategy label matching your absolute best recommended option.
- replies: Exactly 4 genuinely distinct dialogue choices for Kabir's response bubble. Exactly ONE option must have is_recommended=true.

CURRENT SCENE TIMELINE:
- Dialogue Direction/Goal: {direction}
- Current Scene Dialect: {detected_dialect}
- Text Transcript Log:
{transcript_text}
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
            (
                "user",
                "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya",
            ),
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
            (
                "user",
                "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya",
            ),
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
            (
                "user",
                "lucknow mein ho par biryani ya kebabs ke liye ladai pakki hai kya",
            ),
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
    return {
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--temperature", type=float, default=0.75)
    args = ap.parse_args()

    for turn in TURNS:
        payload = build_payload(turn)

        # Format the Scriptwriter system prompt dynamically
        system_prompt = SCRIPTWRITER_GEMINI_PROMPT_TEMPLATE.format(
            person_name=payload["person_name"],
            direction=payload["direction"],
            detected_dialect=payload["analysis"]["detected_dialect"],
            transcript_text=payload["transcript_text"],
        )

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
        except Exception as exc:
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
