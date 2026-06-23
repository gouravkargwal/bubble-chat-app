"""
Offline generator-model eval — compare model WRITING without the full pipeline.

Rebuilds the EXACT production generator prompt (system + human payload) from a
captured payload JSON, then:
  * --dump          writes generator_prompt.txt so you can paste it into ANY model
                    playground (Groq console, OpenRouter free tier, Google AI Studio…)
  * --models a,b,c  calls each Groq model in PLAIN CHAT mode (NO structured output, so
                    no tool-call 400s) and prints raw text side by side. This lets you
                    judge writing quality of EVERY model — including the ones that break
                    structured output in production.

Capture a payload: copy the HumanMessage `content` (the JSON string) from any
`generator_node_llm_messages` log line into a file (default: scripts/sample_payload.json,
which ships with the last Lucknow HINGLISH run).

Run inside the container (deps + GROQ_API_KEY already present):
  docker compose exec api python scripts/eval_models.py --dump
  docker compose exec api python scripts/eval_models.py \
      --models "openai/gpt-oss-120b,qwen/qwen3-32b,meta-llama/llama-4-scout-17b-16e-instruct,llama-3.3-70b-versatile"
"""

from __future__ import annotations

import argparse
import json
import os

from agent.nodes_v2._generator import _build_generator_prompt
from agent.nodes_v2._personality import build_tone_prior
from app.config import settings

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_PAYLOAD = os.path.join(_HERE, "sample_payload.json")

# Plain-chat models can't be forced into the Pydantic schema, so we ask for the JSON
# shape in the prompt and just read whatever comes back. No 400s — writing only.
_JSON_INSTRUCTION = (
    "\n\n---\nRESPOND WITH ONLY THIS JSON (no prose, no markdown fences):\n"
    '{"recommended_strategy_label":"<one label>","hook_point":"...","right_energy":"...",'
    '"wrong_moves":["..."],"replies":[{"text":"...","strategy_label":"<PUSH-PULL|FRAME '
    'CONTROL|SOFT CLOSE|VALUE ANCHOR|PATTERN INTERRUPT|HONEST FRAME>","is_recommended":'
    'true,"coach_reasoning":"..."}]}\nExactly 4 replies; exactly one is_recommended=true.'
)


def _val(d: dict, key: str, default: str) -> str:
    return str(d.get(key) or default)


def build_system_prompt(payload: dict) -> str:
    """Reproduce generator_node's _build_generator_prompt call from a captured payload."""
    analysis = payload.get("analysis", {}) or {}
    ctx = payload.get("conversation_context_dict", {}) or {}
    stable = ctx.get("stable_dimensions") or {}

    def dim(name: str, default: str) -> str:
        return str(stable.get(name) or analysis.get(name) or default)

    personality_prior = build_tone_prior(
        dim("warmth", "neutral"),
        dim("playfulness", "balanced"),
        dim("engagement", "medium"),
        dim("traditionalism", "mixed"),
        dim("intent", "open"),
    )
    return _build_generator_prompt(
        direction=payload.get("direction", "quick_reply"),
        custom_hint=payload.get("user_custom_hint", "") or "",
        detected_dialect=_val(analysis, "detected_dialect", "ENGLISH"),
        stage=_val(analysis, "stage", "early_talking"),
        conversation_temperature=_val(analysis, "conversation_temperature", "warm"),
        their_tone=_val(analysis, "their_tone", "neutral"),
        their_effort=_val(analysis, "their_effort", "medium"),
        preferred_strategies=ctx.get("preferred_strategies") or [],
        personality_prior=personality_prior,
    )


def run_models(
    system_prompt: str, human: str, models: list[str], temperature: float
) -> None:
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1"
    )
    for model in models:
        print("\n" + "=" * 88)
        print(f"MODEL: {model}")
        print("=" * 88)
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt + _JSON_INSTRUCTION},
                    {"role": "user", "content": human},
                ],
            )
            print((resp.choices[0].message.content or "").strip())
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {type(exc).__name__}: {exc}")


def _openrouter_client():
    from openai import OpenAI

    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY not set in .env.dev")
    return OpenAI(
        api_key=settings.openrouter_api_key, base_url="https://openrouter.ai/api/v1"
    )


def run_openrouter(
    system_prompt: str, human: str, models: list[str], temperature: float
) -> None:
    """Plain-chat writing eval via OpenRouter (no schema → reads any model's writing)."""
    client = _openrouter_client()
    for model in models:
        print("\n" + "=" * 88)
        print(f"MODEL (OpenRouter, plain-chat): {model}")
        print("=" * 88)
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt + _JSON_INSTRUCTION},
                    {"role": "user", "content": human},
                ],
            )
            print((resp.choices[0].message.content or "").strip())
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {type(exc).__name__}: {exc}")


def run_reliability(
    system_prompt: str, human: str, models: list[str], trials: int
) -> None:
    """The decisive test: does the model hold the REAL GeneratorOutput Pydantic schema
    (valid strategy_label enum + all required fields) under tool-calling, N times?
    This is what the playground can't show — it 400s on a schema miss, just like prod.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    from agent.nodes_v2._generator import GeneratorOutput

    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY not set in .env.dev")
    msgs = [SystemMessage(content=system_prompt), HumanMessage(content=human)]
    for model in models:
        print("\n" + "=" * 88)
        print(f"RELIABILITY (OpenRouter, structured schema): {model}  ×{trials}")
        print("=" * 88)
        llm = ChatOpenAI(
            model=model,
            temperature=0.85,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        ).with_structured_output(GeneratorOutput, method="function_calling")
        ok = 0
        for i in range(trials):
            try:
                out = llm.invoke(msgs)
                labels = [r.strategy_label for r in out.replies]
                print(
                    f"  trial {i + 1}: ✅ PASS  ({len(out.replies)} replies, labels={labels})"
                )
                ok += 1
            except Exception as exc:  # noqa: BLE001
                short = str(exc)[:260].replace("\n", " ")
                print(f"  trial {i + 1}: ❌ FAIL  {type(exc).__name__}: {short}")
        print(f"  → {ok}/{trials} held the schema")


def run_gemini(system_prompt: str, human: str, temperature: float) -> None:
    """Production path: Gemini + the REAL GeneratorOutput schema. This is what actually
    ships — use it to validate prompt changes on the model you deploy."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from agent.nodes_v2._generator import GeneratorOutput
    from agent.nodes_v2._lc_usage import invoke_structured_gemini

    print("\n" + "=" * 88)
    print(f"MODEL (Gemini, PRODUCTION path + schema): {settings.gemini_model}")
    print("=" * 88)
    msgs = [SystemMessage(content=system_prompt), HumanMessage(content=human)]
    out, _ = invoke_structured_gemini(
        model=settings.gemini_model,
        temperature=temperature,
        schema=GeneratorOutput,
        messages=msgs,
        phase="eval_gemini",
    )
    print(f"recommended_strategy_label: {out.recommended_strategy_label}")
    for r in out.replies:
        star = " ★" if r.is_recommended else "  "
        print(f"{star}[{r.strategy_label}] {r.text}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--payload", default=_DEFAULT_PAYLOAD, help="captured HumanMessage JSON"
    )
    ap.add_argument("--dump", action="store_true", help="write generator_prompt.txt")
    ap.add_argument(
        "--models", default="", help="comma-separated Groq model ids (plain-chat)"
    )
    ap.add_argument(
        "--openrouter",
        default="",
        help="comma-separated OpenRouter model ids (plain-chat)",
    )
    ap.add_argument(
        "--reliability",
        default="",
        help="comma-separated OpenRouter model ids (structured schema test)",
    )
    ap.add_argument(
        "--trials", type=int, default=3, help="reliability trials per model"
    )
    ap.add_argument(
        "--gemini",
        action="store_true",
        help="run the production Gemini path + real schema",
    )
    ap.add_argument("--temperature", type=float, default=0.85)
    args = ap.parse_args()

    with open(args.payload, encoding="utf-8") as f:
        payload = json.load(f)

    system_prompt = build_system_prompt(payload)
    human = json.dumps(payload)

    any_run = args.models or args.openrouter or args.reliability or args.gemini
    if args.dump or not any_run:
        out_path = os.path.join(_HERE, "generator_prompt.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"===== SYSTEM PROMPT =====\n{system_prompt}\n\n")
            f.write(f"===== HUMAN (payload) =====\n{human}\n")
        print(
            f"Wrote {out_path}  (system={len(system_prompt)} chars, "
            f"human={len(human)} chars). Paste both blocks into any model playground."
        )

    if args.models:
        run_models(
            system_prompt,
            human,
            [m.strip() for m in args.models.split(",") if m.strip()],
            args.temperature,
        )
    if args.openrouter:
        run_openrouter(
            system_prompt,
            human,
            [m.strip() for m in args.openrouter.split(",") if m.strip()],
            args.temperature,
        )
    if args.reliability:
        run_reliability(
            system_prompt,
            human,
            [m.strip() for m in args.reliability.split(",") if m.strip()],
            args.trials,
        )
    if args.gemini:
        run_gemini(system_prompt, human, args.temperature)


if __name__ == "__main__":
    main()
