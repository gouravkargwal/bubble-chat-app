"""
RAG retrieval quality evaluator.

Measures how well the RAG read pipeline retrieves expected facts for a given
query. Used by the eval-rag CLI to score retrieval quality changes.

Metrics:
  - HitRate@K:     Was at least one expected fact in top-K?
  - MRR:           Mean Reciprocal Rank — how high was the first relevant result?
  - Precision@K:   What fraction of retrieved results are relevant?
  - Recall@K:      What fraction of relevant facts were retrieved?
  - Entity Recall: Were expected graph entities retrieved?
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import get_match_context
from app.testing.rag_seed_helpers import (
    clean_test_data,
    seed_facts,
    seed_user_and_conversation,
    seed_interactions,
    TEST_USER_ID,
    TEST_CONVERSATION_ID,
    PERSON_NAME,
)

logger = structlog.get_logger(__name__)

SCENARIOS_PATH = Path(__file__).parent.parent / "scenarios" / "scenarios_rag.json"

# Number of top-K results to evaluate (matches _LORE_TOP_K in memory_service.py).
_LORE_TOP_K = 8


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class RAGScenarioResult:
    """Score for a single RAG scenario."""

    scenario_id: str
    variant_id: str
    difficulty: str
    hit_rate: float          # 1.0 if any expected fact in top-K
    mrr: float               # reciprocal rank of first relevant fact
    precision_at_k: float    # relevant / total retrieved
    recall_at_k: float       # relevant / total relevant
    entity_recall: float | None = None  # expected graph entities found
    retrieved_count: int = 0
    expected_count: int = 0
    relevant_retrieved: int = 0
    error: str | None = None


@dataclass
class RAGSuiteResult:
    """Aggregated results for one variant."""

    variant_id: str
    scenario_results: list[RAGScenarioResult] = field(default_factory=list)

    @property
    def avg_hit_rate(self) -> float:
        return (
            sum(r.hit_rate for r in self.scenario_results if not r.error)
            / len([r for r in self.scenario_results if not r.error])
            if self.scenario_results
            else 0.0
        )

    @property
    def avg_mrr(self) -> float:
        scored = [r for r in self.scenario_results if not r.error]
        return sum(r.mrr for r in scored) / len(scored) if scored else 0.0

    @property
    def avg_precision(self) -> float:
        scored = [r for r in self.scenario_results if not r.error]
        return sum(r.precision_at_k for r in scored) / len(scored) if scored else 0.0

    @property
    def avg_recall(self) -> float:
        scored = [r for r in self.scenario_results if not r.error]
        return sum(r.recall_at_k for r in scored) / len(scored) if scored else 0.0

    @property
    def avg_entity_recall(self) -> float | None:
        with_entity = [
            r for r in self.scenario_results
            if not r.error and r.entity_recall is not None
        ]
        if not with_entity:
            return None
        return sum(e.entity_recall for e in with_entity) / len(with_entity)


# ── Evaluator ────────────────────────────────────────────────────────────────


class RAGEvaluator:
    """Score RAG retrieval quality against ground-truth scenarios."""

    def __init__(self, use_llm: bool = True, variant_id: str = "default"):
        self.use_llm = use_llm
        self.variant_id = variant_id

    async def evaluate(
        self,
        db: AsyncSession,
        scenarios: list[dict] | None = None,
    ) -> RAGSuiteResult:
        """Run all scenarios and return scored results."""
        if scenarios is None:
            scenarios = self._load_scenarios()

        suite = RAGSuiteResult(variant_id=self.variant_id)

        for scenario in scenarios:
            sid = scenario["id"]
            difficulty = scenario.get("difficulty", "unknown")
            facts: list[dict] = scenario.get("facts", [])
            query: str = scenario.get("query", "")
            expected_texts: list[str] = scenario.get("expected_fact_texts", [])
            expected_entities: list[str] = scenario.get("expected_graph_entities", [])

            try:
                # Clean and re-seed for each scenario to avoid cross-contamination
                await clean_test_data(db)
                await seed_user_and_conversation(db)
                if facts:
                    await seed_facts(db, facts, use_llm=self.use_llm)
                # Seed default interactions for Tier 1/Tier 2 context
                await seed_interactions(db)

                # Run the RAG read pipeline
                ctx = await get_match_context(
                    db,
                    user_id=TEST_USER_ID,
                    conversation_id=TEST_CONVERSATION_ID,
                    current_text=query,
                )

                core_lore: str = ctx.get("core_lore") or ""
                lore_lines = [
                    ln.strip()
                    for ln in core_lore.split("\n")
                    if ln.strip() and not ln.startswith("===")
                ]

                # Determine if this is a negative scenario (expects NO facts)
                is_negative = scenario.get("is_negative", False)

                # Score
                relevant = 0
                first_rank = 0
                for rank, line in enumerate(lore_lines[: _LORE_TOP_K], start=1):
                    for expected in expected_texts:
                        if expected.lower() in line.lower():
                            relevant += 1
                            if first_rank == 0:
                                first_rank = rank
                            break

                total_retrieved = len(lore_lines[: _LORE_TOP_K])
                total_expected = len(expected_texts) if expected_texts else 1

                if is_negative:
                    # Negative scenario: we expect NO facts from expected_texts
                    # to appear in results.  It's OK to retrieve unrelated facts
                    # (the pipeline always returns top-K), but none should match
                    # the (empty) expected list.
                    hit_rate = 1.0 if relevant == 0 else 0.0
                    mrr = 1.0
                    precision = 1.0
                    recall = 1.0
                else:
                    hit_rate = 1.0 if relevant > 0 else 0.0
                    mrr = 1.0 / first_rank if first_rank > 0 else 0.0
                    precision = relevant / total_retrieved if total_retrieved > 0 else 0.0
                    recall = relevant / total_expected if total_expected > 0 else 0.0

                # Entity recall (if expected entities provided)
                entity_recall: float | None = None
                if expected_entities:
                    lore_lower = core_lore.lower()
                    matched = sum(
                        1 for e in expected_entities if e.lower() in lore_lower
                    )
                    entity_recall = matched / len(expected_entities)

                suite.scenario_results.append(
                    RAGScenarioResult(
                        scenario_id=sid,
                        variant_id=self.variant_id,
                        difficulty=difficulty,
                        hit_rate=hit_rate,
                        mrr=mrr,
                        precision_at_k=precision,
                        recall_at_k=recall,
                        entity_recall=entity_recall,
                        retrieved_count=total_retrieved,
                        expected_count=total_expected,
                        relevant_retrieved=relevant,
                    )
                )

            except Exception as e:
                logger.warning("rag_scenario_failed", scenario_id=sid, error=str(e))
                suite.scenario_results.append(
                    RAGScenarioResult(
                        scenario_id=sid,
                        variant_id=self.variant_id,
                        difficulty=difficulty,
                        hit_rate=0.0,
                        mrr=0.0,
                        precision_at_k=0.0,
                        recall_at_k=0.0,
                        error=str(e),
                    )
                )

        return suite

    @staticmethod
    def _load_scenarios() -> list[dict]:
        """Load scenarios from the JSON file."""
        if not SCENARIOS_PATH.exists():
            logger.warning("scenarios_rag_not_found", path=str(SCENARIOS_PATH))
            return []
        with open(SCENARIOS_PATH) as f:
            return json.load(f)

    @staticmethod
    def load_scenarios_by_difficulty(
        difficulty: str | None = None,
    ) -> list[dict]:
        """Load and optionally filter scenarios by difficulty."""
        scenarios = RAGEvaluator._load_scenarios()
        if difficulty:
            scenarios = [s for s in scenarios if s.get("difficulty") == difficulty]
        return scenarios


# ── Report ────────────────────────────────────────────────────────────────────


def format_report(suite: RAGSuiteResult, other_suite: RAGSuiteResult | None = None) -> str:
    """Format evaluation results as a human-readable report string."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("   RAG QUALITY EVALUATION")
    lines.append("=" * 72)
    lines.append("")

    # Per-scenario table
    header = f"{'Scenario':<40} {'Difficulty':<12} {'HitRate':<8} {'MRR':<8} {'P@8':<8} {'R@8':<8}"
    lines.append(header)
    lines.append("-" * 72)
    for r in suite.scenario_results:
        if r.error:
            lines.append(f"  {r.scenario_id:<40} {'ERROR':<12} {r.error[:50]}")
        else:
            lines.append(
                f"  {r.scenario_id:<40} {r.difficulty:<12} "
                f"{r.hit_rate:<8.3f} {r.mrr:<8.3f} "
                f"{r.precision_at_k:<8.3f} {r.recall_at_k:<8.3f}"
            )
    lines.append("-" * 72)
    lines.append(
        f"{'AVERAGE':<40} {'':<12} "
        f"{suite.avg_hit_rate:<8.3f} {suite.avg_mrr:<8.3f} "
        f"{suite.avg_precision:<8.3f} {suite.avg_recall:<8.3f}"
    )
    lines.append("")

    # Entity recall
    if suite.avg_entity_recall is not None:
        lines.append(f"  Entity Recall: {suite.avg_entity_recall:.3f}")
    lines.append("")

    # Variant comparison
    if other_suite:
        lines.append("═" * 72)
        lines.append("   VARIANT COMPARISON")
        lines.append("═" * 72)
        lines.append(f"{'Metric':<20} {'Before':<10} {'After':<10} {'Δ':<10}")
        lines.append("-" * 50)
        for metric, before_val, after_val in [
            ("Avg HitRate", other_suite.avg_hit_rate, suite.avg_hit_rate),
            ("Avg MRR", other_suite.avg_mrr, suite.avg_mrr),
            ("Avg Precision", other_suite.avg_precision, suite.avg_precision),
            ("Avg Recall", other_suite.avg_recall, suite.avg_recall),
        ]:
            delta = after_val - before_val
            arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
            lines.append(
                f"  {metric:<20} {before_val:<10.3f} {after_val:<10.3f} "
                f"{delta:<+8.3f} {arrow}"
            )

        if other_suite.avg_entity_recall is not None and suite.avg_entity_recall is not None:
            delta_ent = suite.avg_entity_recall - other_suite.avg_entity_recall
            arrow_ent = "↑" if delta_ent > 0 else ("↓" if delta_ent < 0 else "→")
            lines.append(
                f"  {'Entity Recall':<20} {other_suite.avg_entity_recall:<10.3f} "
                f"{suite.avg_entity_recall:<10.3f} {delta_ent:<+8.3f} {arrow_ent}"
            )

        lines.append("")

        # Verdict
        improved = (
            suite.avg_hit_rate >= other_suite.avg_hit_rate
            and suite.avg_mrr >= other_suite.avg_mrr
        )
        lines.append(
            f"  VERDICT: {'CHANGE IS AN IMPROVEMENT ✓' if improved else 'NEUTRAL OR REGRESSION ✗'}"
        )
        lines.append("")

    lines.append("=" * 72)
    lines.append("")

    return "\n".join(lines)
