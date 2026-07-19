"""
CLI entry point: python -m scripts.eval_rag_quality

Evaluates RAG retrieval quality against ground-truth scenarios.

Usage:
    python -m scripts.eval_rag_quality
    python -m scripts.eval_rag_quality --variants before after
    python -m scripts.eval_rag_quality --difficulty hard
    python -m scripts.eval_rag_quality --use-cache
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# ── Bootstrap: patch hostname before pydantic-settings reads the env file ────
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, ".."))
_env_url = os.getenv("DATABASE_URL") or ""
if not _env_url:
    _env_file = os.getenv("ENV_FILE", "")
    if not _env_file:
        for _candidate in (
            os.path.join(_project_root, ".env.dev"),
            os.path.join(_project_root, "..", ".env.dev"),
            os.path.join(_project_root, ".env"),
        ):
            if os.path.isfile(_candidate):
                _env_file = _candidate
                break
    if _env_file and os.path.isfile(_env_file):
        for _line in open(_env_file):
            if _line.startswith("DATABASE_URL="):
                _env_url = _line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if "@postgres:" in _env_url:
    _env_url = _env_url.replace("@postgres:", "@localhost:")
    os.environ["DATABASE_URL"] = _env_url

from app.config import settings

if settings.gemini_api_key:
    os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)
    if "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key

from app.infrastructure.database.engine import async_session, init_db
from app.testing.evaluators.rag_evaluator import (
    RAGEvaluator,
    format_report,
)
from app.testing.rag_seed_helpers import clean_test_data

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s  %(message)s",
    force=True,
)
# Silence noisy loggers
for noisy in ("httpx", "httpcore", "google_genai", "app", "agent"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("eval_rag_quality")


async def run_variant(
    db, variant_id: str, difficulty: str | None, use_llm: bool
):
    """Run a single variant and return the suite result."""
    from sqlalchemy import text
    from app.infrastructure.database.models import Base
    from app.infrastructure.database.engine import engine as _eng

    async with _eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)

    evaluator = RAGEvaluator(use_llm=use_llm, variant_id=variant_id)
    scenarios = evaluator.load_scenarios_by_difficulty(difficulty)
    if not scenarios:
        logger.error("No scenarios found (difficulty=%s)", difficulty)
        return None

    print(f"\n[{variant_id}] Evaluating {len(scenarios)} scenarios...\n")
    suite = await evaluator.evaluate(db, scenarios)
    return suite


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG Retrieval Quality Evaluation"
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        default=["default"],
        help="Variant IDs to evaluate (default: 'default'). "
        "Use '--variants before after' to compare.",
    )
    parser.add_argument(
        "--difficulty",
        type=str,
        default=None,
        choices=["easy", "medium", "hard"],
        help="Filter scenarios by difficulty level.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        default=False,
        help="Use mock embeddings (no Gemini API calls).",
    )
    args = parser.parse_args()

    use_llm = not args.no_llm
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set. Falling back to mock embeddings.")
        use_llm = False

    async with async_session() as db:
        suites: list = []
        for vid in args.variants:
            suite = await run_variant(db, vid, args.difficulty, use_llm)
            if suite:
                suites.append(suite)
            # Clean between variants
            await clean_test_data(db)

    # Print reports
    if len(suites) == 2:
        print(format_report(suites[1], suites[0]))
    elif suites:
        print(format_report(suites[0]))

    # Summary
    if suites:
        suite = suites[-1]
        total = len(suite.scenario_results)
        passed = sum(1 for r in suite.scenario_results if r.hit_rate > 0 and not r.error)
        print(f"\n  Scenarios: {total}  |  Hit: {passed}  |  "
              f"Avg MRR: {suite.avg_mrr:.3f}  |  "
              f"Avg P@8: {suite.avg_precision:.3f}\n")


if __name__ == "__main__":
    asyncio.run(main())
