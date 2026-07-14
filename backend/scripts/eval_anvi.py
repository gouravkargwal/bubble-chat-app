"""
Run the full generator + auditor pipeline on the Anvi opener payload.

This simulates exactly what happens in production (same nodes, same prompts)
but skips vision/OCR and uses the captured payload directly.

Run inside the container:
  docker compose exec api python scripts/eval_anvi.py
  docker compose exec api python scripts/eval_anvi.py --payload scripts/anvi_payload.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_PAYLOAD = os.path.join(_HERE, "anvi_payload.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agent.nodes_v2._auditor import auditor_node
from agent.nodes_v2._generator import generator_node
from agent.state import AnalystOutput

# ────────────────────────────────────────────────────────────────────────────
# Colours for terminal output
# ────────────────────────────────────────────────────────────────────────────
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _print_banner(text: str, char: str = "=") -> None:
    print(f"\n{_CYAN}{_BOLD}{char * 72}")
    print(f"  {text}")
    print(f"{char * 72}{_RESET}\n")


def _load_payload(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_initial_state(payload: dict) -> dict:
    """Build the minimal AgentState dict needed by generator_node + auditor_node."""
    analysis_dict = payload.get("analysis", {})
    analysis = AnalystOutput(**analysis_dict)

    return {
        "user_id": "eval",
        "conversation_id": None,
        "direction": payload.get("direction", "opener"),
        "custom_hint": payload.get("user_custom_hint", "") or "",
        "voice_dna_dict": payload.get("voice_dna_dict", {}),
        "conversation_context_dict": payload.get("conversation_context_dict", {}),
        "core_lore": payload.get("core_lore", "") or "",
        "past_memories": payload.get("past_memories", "") or "",
        "analysis": analysis,
        "revision_count": 0,
        "auditor_feedback": "",
        "is_cringe": False,
        "drafts": None,
        "gemini_usage_log": [],
    }


def print_generator_output(state: dict) -> None:
    """Print the generator output in a readable format."""
    strategy = state.get("strategy")
    drafts = state.get("drafts")

    if strategy:
        print(f"  {_YELLOW}Wrong moves:{_RESET}")
        for m in strategy.wrong_moves:
            print(f"    · {m}")
        print(f"\n  {_YELLOW}Right energy:{_RESET} {strategy.right_energy}")
        print(f"  {_YELLOW}Hook point:{_RESET} {strategy.hook_point}")
        print(f"  {_YELLOW}Recommended strategy:{_RESET} {strategy.recommended_strategy_label}")

    if drafts:
        print(f"\n  {_BOLD}REPLIES:{_RESET}")
        for i, r in enumerate(drafts.replies[:4]):
            star = f"{_GREEN}★{_RESET}" if r.is_recommended else " "
            wc = len(r.text.split())
            print(f"  {star}  [{r.strategy_label}] ({wc}w) {r.text}")
            print(f"       {r.coach_reasoning}")

    # Print token usage
    usage_log = state.get("gemini_usage_log", [])
    if usage_log:
        u = usage_log[0]
        print(
            f"\n  {_CYAN}Token usage:{_RESET} prompt={u.get('prompt_tokens', '?')}  "
            f"candidates={u.get('candidates_tokens', '?')}  "
            f"cost=${u.get('cost_usd', 0):.6f}"
        )


def print_auditor_output(state: dict) -> None:
    """Print the auditor output in a readable format."""
    auditor_feedback = state.get("auditor_feedback", "")
    is_cringe = state.get("is_cringe", False)

    if is_cringe:
        print(f"\n  {_RED}{_BOLD}AUDITOR: FAILED — rewrite needed{_RESET}")
    else:
        print(f"\n  {_GREEN}{_BOLD}AUDITOR: PASSED — all replies approved{_RESET}")

    if auditor_feedback:
        print(f"\n  {_YELLOW}Feedback:{_RESET}")
        for line in auditor_feedback.split("\n"):
            if line.strip():
                print(f"    {line}")

    usage_log = state.get("gemini_usage_log", [])
    if len(usage_log) > 1:
        u = usage_log[1]
        print(
            f"\n  {_CYAN}Token usage:{_RESET} prompt={u.get('prompt_tokens', '?')}  "
            f"candidates={u.get('candidates_tokens', '?')}  "
            f"cost=${u.get('cost_usd', 0):.6f}"
        )


def run_rewrite_cycle(state: dict) -> dict:
    """If the auditor failed, run one rewrite cycle and re-audit."""
    if not state.get("is_cringe", False):
        return state

    print(f"\n  {_YELLOW}{_BOLD}→ Auditor rejected. Running rewrite...{_RESET}\n")
    t0 = time.monotonic()
    gen_out = generator_node(state)
    state.update(gen_out)
    t_gen = time.monotonic() - t0

    print(f"  {_BOLD}REWRITE OUTPUT (generated in {t_gen:.1f}s):{_RESET}")
    print_generator_output(state)

    t0 = time.monotonic()
    audit_out = auditor_node(state)
    state.update(audit_out)
    t_audit = time.monotonic() - t0

    print_auditor_output(state)
    return state


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--payload",
        default=_DEFAULT_PAYLOAD,
        help=f"payload JSON file (default: {_DEFAULT_PAYLOAD})",
    )
    ap.add_argument(
        "--rewrite",
        action="store_true",
        default=True,
        help="run a rewrite cycle if auditor fails (default: True)",
    )
    ap.add_argument(
        "--no-rewrite",
        action="store_false",
        dest="rewrite",
        help="skip rewrite cycle",
    )
    args = ap.parse_args()

    # ── Load payload ──────────────────────────────────────────────────────
    print(f"{_BOLD}Loading payload: {args.payload}{_RESET}")
    payload = _load_payload(args.payload)
    person_name = payload.get("person_name", "unknown")
    direction = payload.get("direction", "quick_reply")

    print(f"  Person: {person_name}")
    print(f"  Direction: {direction}")
    print(f"  Dialect: {payload.get('analysis', {}).get('detected_dialect', 'ENGLISH')}")
    print(f"  Archetype: {payload.get('analysis', {}).get('detected_archetype', 'N/A')}")
    print(f"  Photo persona: {payload.get('analysis', {}).get('photo_persona', 'N/A')}")
    print(f"  Interaction count: {payload.get('conversation_context_dict', {}).get('interaction_count', 0)}")
    print(f"  Stale replies in history: {len(payload.get('conversation_context_dict', {}).get('last_ai_replies_shown', []))}")

    # ── Generator ─────────────────────────────────────────────────────────
    _print_banner(f"PHASE 1: GENERATOR — {person_name} ({direction})", "─")
    state = build_initial_state(payload)

    t0 = time.monotonic()
    print(f"{_BOLD}Calling generator_node...{_RESET}")
    gen_out = generator_node(state)
    state.update(gen_out)
    t_gen = time.monotonic() - t0

    revision_count = state.get("revision_count", 0)
    print(f"\n  {_BOLD}FIRST PASS OUTPUT (generated in {t_gen:.1f}s, revision #{revision_count}):{_RESET}")
    print_generator_output(state)

    # ── Auditor ───────────────────────────────────────────────────────────
    _print_banner("PHASE 2: AUDITOR — quality evaluation", "─")

    t0 = time.monotonic()
    print(f"{_BOLD}Calling auditor_node...{_RESET}")
    audit_out = auditor_node(state)
    state.update(audit_out)
    t_audit = time.monotonic() - t0

    print(f"\n  {_BOLD}AUDITOR RESULT (completed in {t_audit:.1f}s):{_RESET}")
    print_auditor_output(state)

    # ── Rewrite (if auditor failed) ───────────────────────────────────────
    if args.rewrite:
        state = run_rewrite_cycle(state)

    # ── Final summary (post-processed) ────────────────────────────────────
    _print_banner("FINAL SHIPPED REPLIES (after post-processing)", "=")

    drafts = state.get("drafts")
    if drafts:
        from agent.nodes_v2._post_processor import post_process_replies
        from agent.state import WriterOutput as _WO
        cleaned = post_process_replies(_WO(replies=drafts.replies[:4]))

        print(f"  {'':>4} {'Orig':>5} {'Post':>5}  Reply")
        print(f"  {'':>4} {'─────':>5} {'─────':>5}  ─────")
        for i, r in enumerate(cleaned.replies):
            star = f"{_GREEN}★{_RESET}" if r.is_recommended else " "
            orig_wc = len(drafts.replies[i].text.split())
            post_wc = len(r.text.split())
            clamped = f"{_RED} CLAMPED{_RESET}" if post_wc < orig_wc else ""
            print(f"  {star} {orig_wc:>3}w → {post_wc:>2}w{clamped}  [{r.strategy_label}] {r.text}")
            print(f"       {r.coach_reasoning}")
    else:
        print(f"  {_RED}No drafts generated.{_RESET}")

    is_cringe = state.get("is_cringe", False)
    final_status = (
        f"{_GREEN}{_BOLD}APPROVED ✓{_RESET}"
        if not is_cringe
        else f"{_RED}{_BOLD}UNRESOLVED ISSUES ✗{_RESET}"
    )
    print(f"\n  {_BOLD}Final audit status:{_RESET} {final_status}")
    if is_cringe:
        print(f"  {_BOLD}Note:{_RESET} shipped with issues (production behavior)")

    total_ms = (t_gen + t_audit) * 1000
    all_usage = state.get("gemini_usage_log", [])
    total_cost = sum(u.get("cost_usd", 0) for u in all_usage)
    print(f"\n  {_BOLD}Pipeline summary:{_RESET}")
    print(f"    Gemini calls: {len(all_usage)}")
    print(f"    Total latency: {total_ms:.0f}ms")
    print(f"    Total cost: ${total_cost:.6f}")


if __name__ == "__main__":
    main()
