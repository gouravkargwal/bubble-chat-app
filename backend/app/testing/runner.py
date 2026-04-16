"""Test runner — calls generator_node + auditor_node directly, skipping vision/OCR."""

import asyncio
import json
import time
from dataclasses import dataclass, field

import structlog

from app.config import settings
from app.testing.cache import clear as cache_clear
from app.testing.cache import get as cache_get
from app.testing.cache import put as cache_put
from app.testing.cache import scenario_hash
from app.testing.evaluators.llm_judge import JudgeReport, ReplyScore
from app.testing.evaluators.llm_judge import evaluate as judge_evaluate
from app.testing.scenarios.dataset import (
    Scenario,
    build_analyst_output,
    get_all,
    get_by_category,
    get_by_id,
)

logger = structlog.get_logger()

# Rate limits:
#   Gemini (generator + auditor): 15 RPM → 4s min → use 4.5s
#   Groq (judge): 30 RPM → 2s min → Gemini is the bottleneck, 4.5s covers both
#   Gemini RPD: 500 → 50 scenarios × 2 calls = 100 (safe)
#   Groq RPD: 14,400 → 50 × 1 = 50 (safe)
_INTER_CALL_DELAY_SECONDS = 4.5  # Gemini-bound: 60 / 15 RPM + 0.5s buffer


@dataclass
class RunResult:
    scenario_id: str
    variant_id: str
    run_index: int
    replies: list[str]
    judge_report: JudgeReport | None = None
    auditor_passes: bool | None = None  # None = auditor skipped
    auditor_feedback: str = ""
    latency_ms: int = 0
    error: str | None = None


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    variant_id: str
    runs: list[RunResult] = field(default_factory=list)

    @property
    def avg_judge_score(self) -> float:
        scores = [
            r.judge_report.overall_score
            for r in self.runs
            if r.judge_report and not r.error
        ]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def avg_specificity(self) -> float:
        scores = [
            sum(s.specificity for s in r.judge_report.reply_scores)
            / len(r.judge_report.reply_scores)
            for r in self.runs
            if r.judge_report and r.judge_report.reply_scores and not r.error
        ]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def avg_human_voice(self) -> float:
        scores = [
            sum(s.human_voice for s in r.judge_report.reply_scores)
            / len(r.judge_report.reply_scores)
            for r in self.runs
            if r.judge_report and r.judge_report.reply_scores and not r.error
        ]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def avg_usability(self) -> float:
        scores = [
            sum(s.usability for s in r.judge_report.reply_scores)
            / len(r.judge_report.reply_scores)
            for r in self.runs
            if r.judge_report and r.judge_report.reply_scores and not r.error
        ]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def auditor_pass_rate(self) -> float:
        results = [r.auditor_passes for r in self.runs if r.auditor_passes is not None]
        return sum(results) / len(results) if results else 0.0


@dataclass
class TestSuiteResult:
    variant_results: dict[str, list[ScenarioResult]] = field(default_factory=dict)

    def get_variant_summary(self, variant_id: str) -> dict:
        results = self.variant_results.get(variant_id, [])
        if not results:
            return {}
        scored = [r for r in results if r.avg_judge_score > 0]
        return {
            "variant": variant_id,
            "scenarios_tested": len(results),
            "avg_judge_score": sum(r.avg_judge_score for r in results) / len(results),
            "avg_specificity": sum(r.avg_specificity for r in results) / len(results),
            "avg_human_voice": sum(r.avg_human_voice for r in results) / len(results),
            "avg_usability": sum(r.avg_usability for r in results) / len(results),
            "auditor_pass_rate": sum(r.auditor_pass_rate for r in results)
            / len(results),
            "worst_scenario": (
                min(results, key=lambda r: r.avg_judge_score).scenario_id
                if scored
                else "N/A"
            ),
            "best_scenario": (
                max(results, key=lambda r: r.avg_judge_score).scenario_id
                if scored
                else "N/A"
            ),
        }


class TestRunner:
    def __init__(
        self,
        model: str | None = None,
        inter_call_delay: float = _INTER_CALL_DELAY_SECONDS,
        use_cache: bool = True,
    ) -> None:
        self.model = model or settings.gemini_model
        self.inter_call_delay = inter_call_delay
        self.use_cache = use_cache

    async def run(
        self,
        variant_ids: list[str] | None = None,
        scenario_ids: list[str] | None = None,
        category: str | None = None,
        runs_per_combo: int = 1,
        judge_model: str | None = None,
    ) -> TestSuiteResult:
        """Run evaluation across variants × scenarios × N runs."""
        if scenario_ids:
            scenarios = [s for s in get_all() if s.id in scenario_ids]
        elif category:
            scenarios = get_by_category(category)
        else:
            scenarios = get_all()

        if variant_ids is None:
            variant_ids = ["default"]

        suite_result = TestSuiteResult()

        for variant_id in variant_ids:
            logger.info("testing_variant", variant=variant_id, scenarios=len(scenarios))
            scenario_results: list[ScenarioResult] = []

            for scenario in scenarios:
                scenario_result = ScenarioResult(
                    scenario_id=scenario.id,
                    category=scenario.category,
                    variant_id=variant_id,
                )

                for run_idx in range(runs_per_combo):
                    run_result = await self._run_single(
                        scenario=scenario,
                        variant_id=variant_id,
                        run_index=run_idx,
                        judge_model=judge_model,
                    )
                    if run_result is None:
                        logger.warning("scenario_skipped", scenario=scenario.id)
                        continue
                    scenario_result.runs.append(run_result)

                    # gen + audit + judge = 3 calls per run
                    await asyncio.sleep(self.inter_call_delay * 3)

                if not scenario_result.runs:
                    logger.warning(
                        "scenario_dropped",
                        scenario=scenario.id,
                        reason="all runs failed",
                    )
                    continue

                scenario_results.append(scenario_result)
                logger.info(
                    "scenario_complete",
                    scenario=scenario.id,
                    variant=variant_id,
                    avg_judge=f"{scenario_result.avg_judge_score:.1f}",
                    avg_usability=f"{scenario_result.avg_usability:.1f}",
                    auditor_pass_rate=f"{scenario_result.auditor_pass_rate:.0%}",
                )

            suite_result.variant_results[variant_id] = scenario_results

        return suite_result

    async def _run_single(
        self,
        scenario: Scenario,
        variant_id: str,
        run_index: int,
        judge_model: str | None,
        _retry: int = 0,
    ) -> RunResult | None:
        """Call generator_node + auditor_node directly with a mock AnalystOutput.

        Skips vision/OCR entirely — tests the prompt quality of the generator
        and auditor, which is what determines reply quality in production.

        Returns None if the run should be skipped (capacity error after retries).
        """
        s_hash = scenario_hash(scenario.model_dump())

        # --- Cache read ---
        if self.use_cache:
            cached = cache_get(scenario.id, variant_id, run_index, s_hash)
            if cached:
                logger.info(
                    "cache_hit",
                    scenario=scenario.id,
                    variant=variant_id,
                )
                judge_report = None
                if cached["judge_report"]:
                    jr_data = json.loads(cached["judge_report"])
                    reply_scores = [
                        ReplyScore(**s) for s in jr_data.get("reply_scores", [])
                    ]
                    judge_report = JudgeReport(
                        reply_scores=reply_scores,
                        overall_score=jr_data["overall_score"],
                        best_reply_index=jr_data["best_reply_index"],
                        worst_reply_index=jr_data["worst_reply_index"],
                        improvement_notes=jr_data.get("improvement_notes", ""),
                    )
                return RunResult(
                    scenario_id=scenario.id,
                    variant_id=variant_id,
                    run_index=run_index,
                    replies=json.loads(cached["replies"]),
                    judge_report=judge_report,
                    auditor_passes=(
                        bool(cached["auditor_passes"])
                        if cached["auditor_passes"] is not None
                        else None
                    ),
                    auditor_feedback=cached["auditor_feedback"] or "",
                    latency_ms=cached["latency_ms"] or 0,
                )

        _RATE_LIMIT_BACKOFFS = [15, 30, 60]
        try:
            from agent.nodes_v2._generator import generator_node
            from agent.nodes_v2._auditor import auditor_node
            from agent.state import AnalystOutput

            # Build mock analyst output from scenario metadata
            analyst_dict = build_analyst_output(scenario)
            analysis = AnalystOutput(**analyst_dict)

            # Minimal AgentState for generator
            state: dict = {
                "trace_id": f"eval_{scenario.id}_{run_index}",
                "user_id": "eval",
                "conversation_id": None,
                "direction": scenario.direction,
                "custom_hint": "",
                "voice_dna_dict": {},
                "conversation_context_dict": {},
                "core_lore": "",
                "past_memories": "",
                "analysis": analysis,
                "revision_count": 0,
                "auditor_feedback": "",
                "is_cringe": False,
                "drafts": None,
                "gemini_usage_log": [],
            }

            # --- Generator call ---
            start = time.monotonic()
            gen_out = await asyncio.to_thread(generator_node, state)
            latency_ms = int((time.monotonic() - start) * 1000)
            state.update(gen_out)

            # --- Auditor call ---
            await asyncio.sleep(self.inter_call_delay)
            audit_out = await asyncio.to_thread(auditor_node, state)

            # Extract replies
            drafts = state.get("drafts")
            if drafts is None:
                raise ValueError("generator_node returned no drafts")

            reply_strings = [r.text for r in drafts.replies[:4]]
            auditor_passes = not audit_out.get("is_cringe", False)
            auditor_feedback = audit_out.get("auditor_feedback", "")

            # --- LLM judge (always runs) ---
            judge_report = None
            await asyncio.sleep(self.inter_call_delay)
            try:
                judge_report = await judge_evaluate(
                    scenario=scenario,
                    replies=reply_strings,
                    judge_model=judge_model,
                )
            except Exception as je:
                logger.warning("judge_failed", scenario=scenario.id, error=str(je))

            # --- Cache write (only when judge succeeded) ---
            if self.use_cache and judge_report is not None:
                from dataclasses import asdict
                jr_dict = asdict(judge_report)
                cache_put(
                    scenario_id=scenario.id,
                    variant_id=variant_id,
                    run_index=run_index,
                    s_hash=s_hash,
                    replies=reply_strings,
                    judge_report_dict=jr_dict,
                    auditor_passes=auditor_passes,
                    auditor_feedback=auditor_feedback,
                    latency_ms=latency_ms,
                )

            return RunResult(
                scenario_id=scenario.id,
                variant_id=variant_id,
                run_index=run_index,
                replies=reply_strings,
                judge_report=judge_report,
                auditor_passes=auditor_passes,
                auditor_feedback=auditor_feedback,
                latency_ms=latency_ms,
            )

        except Exception as e:
            err = str(e)
            is_capacity = (
                "capacity error" in err.lower() or "429" in err or "503" in err
            )
            if is_capacity and _retry < len(_RATE_LIMIT_BACKOFFS):
                wait = _RATE_LIMIT_BACKOFFS[_retry]
                logger.warning(
                    "rate_limit_backoff",
                    scenario=scenario.id,
                    retry=_retry + 1,
                    wait_seconds=wait,
                )
                await asyncio.sleep(wait)
                return await self._run_single(
                    scenario=scenario,
                    variant_id=variant_id,
                    run_index=run_index,
                    judge_model=judge_model,
                    _retry=_retry + 1,
                )
            logger.error("run_failed_skip", scenario=scenario.id, error=err)
            return None

    async def close(self) -> None:
        pass  # no persistent client to close
