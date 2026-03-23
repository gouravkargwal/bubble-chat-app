"""CLI entry point: python -m app.testing"""

import asyncio
import argparse
import sys

from app.config import settings
from app.infrastructure.logging import setup_logging


async def main() -> None:
    parser = argparse.ArgumentParser(description="RizzBot Prompt Evaluation Suite")
    parser.add_argument("--variants", nargs="+", default=["default"], help="Prompt variants to test")
    parser.add_argument("--category", type=str, default=None, help="Filter scenarios by category")
    parser.add_argument("--scenarios", nargs="+", default=None, help="Specific scenario IDs")
    parser.add_argument("--runs", type=int, default=1, help="Runs per scenario×variant combo")
    parser.add_argument("--judge", action="store_true", help="Enable LLM judge evaluation")
    parser.add_argument("--api-key", type=str, default=None, help="Gemini API key override")
    parser.add_argument("--model", type=str, default=None, help="Model override")
    parser.add_argument(
        "--judge-model",
        type=str,
        default=settings.gemini_model,
        help=f"Judge model (default: GEMINI_MODEL / {settings.gemini_model})",
    )
    args = parser.parse_args()

    setup_logging("INFO", json_logs=False)

    from app.testing.runner import TestRunner
    from app.testing.reporter import generate_report

    runner = TestRunner(gemini_api_key=args.api_key, model=args.model)

    try:
        print(f"\nRunning evaluation...")
        print(f"  Variants: {args.variants}")
        print(f"  Category: {args.category or 'all'}")
        print(f"  Runs per combo: {args.runs}")
        print(f"  LLM Judge: {'enabled (' + args.judge_model + ')' if args.judge else 'disabled'}")
        print()

        result = await runner.run(
            variant_ids=args.variants,
            scenario_ids=args.scenarios,
            category=args.category,
            runs_per_combo=args.runs,
            use_judge=args.judge,
            judge_model=args.judge_model,
        )

        report = generate_report(result)
        print(report)

    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
