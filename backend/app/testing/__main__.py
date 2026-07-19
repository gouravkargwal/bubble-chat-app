"""CLI entry point: python -m app.testing"""

import asyncio
import argparse
import os

# Patch DATABASE_URL for local runs: replace 'postgres' host with 'localhost'.
# This must happen before from app.config import settings so pydantic-settings
# reads the corrected value from the env.
_env_url = os.getenv("DATABASE_URL") or ""
if not _env_url:
    # Read the env file ourselves to find DATABASE_URL
    _env_file = os.getenv("ENV_FILE", "")
    if not _env_file:
        for _candidate in (".env.dev", "../.env.dev", "../.env", ".env"):
            if os.path.isfile(_candidate):
                _env_file = _candidate
                break
    if _env_file and os.path.isfile(_env_file):
        for _line in open(_env_file):
            if _line.startswith("DATABASE_URL="):
                _env_url = _line.split("=", 1)[1].strip().strip('"').strip("'")
                break
if "@postgres:" in _env_url:
    os.environ["DATABASE_URL"] = _env_url.replace("@postgres:", "@localhost:")

from app.config import settings
from app.infrastructure.logging import setup_logging


async def main() -> None:
    parser = argparse.ArgumentParser(description="RizzBot Prompt Evaluation Suite")
    parser.add_argument("--variants", nargs="+", default=["default"], help="Prompt variants to test")
    parser.add_argument("--category", type=str, default=None, help="Filter scenarios by category")
    parser.add_argument("--scenarios", nargs="+", default=None, help="Specific scenario IDs")
    parser.add_argument("--runs", type=int, default=1, help="Runs per scenario×variant combo")
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Seconds between API calls (default: 4.5 — respects Gemini 15 RPM)",
    )
    parser.add_argument("--model", type=str, default=None, help="Generator model override")
    parser.add_argument(
        "--judge-model",
        type=str,
        default=settings.groq_model,
        help=f"Groq judge model (default: {settings.groq_model})",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        default=False,
        help="Ignore cache and re-run all scenarios",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        default=False,
        help="Clear all cached results and exit",
    )
    args = parser.parse_args()

    setup_logging("WARNING", json_logs=False)

    # Silence noisy LLM/agent lifecycle logs during eval — only show warnings+
    import logging
    for noisy in ("agent", "google_genai", "httpx", "httpcore", "app.prompts"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    from app.testing.cache import clear as cache_clear
    from app.testing.runner import TestRunner, _INTER_CALL_DELAY_SECONDS
    from app.testing.reporter import generate_report
    from app.infrastructure.database.engine import async_session

    if args.clear_cache:
        count = cache_clear()
        print(f"Cache cleared ({count} rows deleted).")
        return

    delay = args.delay if args.delay is not None else _INTER_CALL_DELAY_SECONDS
    use_cache = not args.fresh

    runner = TestRunner(
        model=args.model,
        inter_call_delay=delay,
        use_cache=use_cache,
    )

    print(f"\nRunning evaluation...")
    print(f"  Variants:         {args.variants}")
    print(f"  Category:         {args.category or 'all'}")
    print(f"  Runs per combo:   {args.runs}")
    print(f"  Judge:            Groq / {args.judge_model}")
    print(f"  Inter-call delay: {delay}s")
    print(f"  Cache:            {'disabled (--fresh)' if args.fresh else 'enabled'}")
    print()

    try:
        # Try to attach a DB session for RAG context seeding
        async with async_session() as session:
            runner.db = session
            result = await runner.run(
                variant_ids=args.variants,
                scenario_ids=args.scenarios,
                category=args.category,
                runs_per_combo=args.runs,
                judge_model=args.judge_model,
            )
            report = generate_report(result)
            print(report)
    except Exception:
        # DB unavailable — run without RAG context
        runner.db = None
        result = await runner.run(
            variant_ids=args.variants,
            scenario_ids=args.scenarios,
            category=args.category,
            runs_per_combo=args.runs,
            judge_model=args.judge_model,
        )
        report = generate_report(result)
        print(report)


if __name__ == "__main__":
    asyncio.run(main())
