"""CLI entry point: python -m app.testing"""

import asyncio
import argparse

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

    setup_logging("INFO", json_logs=False)

    from app.testing.cache import clear as cache_clear
    from app.testing.runner import TestRunner, _INTER_CALL_DELAY_SECONDS
    from app.testing.reporter import generate_report

    if args.clear_cache:
        count = cache_clear()
        print(f"Cache cleared ({count} rows deleted).")
        return

    delay = args.delay if args.delay is not None else _INTER_CALL_DELAY_SECONDS
    use_cache = not args.fresh
    runner = TestRunner(model=args.model, inter_call_delay=delay, use_cache=use_cache)

    try:
        print(f"\nRunning evaluation...")
        print(f"  Variants:         {args.variants}")
        print(f"  Category:         {args.category or 'all'}")
        print(f"  Runs per combo:   {args.runs}")
        print(f"  Judge:            Groq / {args.judge_model}")
        print(f"  Inter-call delay: {delay}s")
        print(f"  Cache:            {'disabled (--fresh)' if args.fresh else 'enabled'}")
        print()

        result = await runner.run(
            variant_ids=args.variants,
            scenario_ids=args.scenarios,
            category=args.category,
            runs_per_combo=args.runs,
            judge_model=args.judge_model,
        )

        report = generate_report(result)
        print(report)

    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
