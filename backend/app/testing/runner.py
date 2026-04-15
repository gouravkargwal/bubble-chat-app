"""Test runner — runs prompt variants × scenarios × N runs and generates reports."""

import asyncio
import time
from dataclasses import dataclass, field

import structlog

from app.config import settings
from app.llm.gemini_client import GeminiClient
from app.llm.response_parser import parse_llm_response
from app.prompts.engine import prompt_engine
from app.prompts.variants import registry
from app.testing.evaluators import rule_based
from app.testing.evaluators.llm_judge import JudgeReport
from app.testing.evaluators.llm_judge import evaluate as judge_evaluate
from app.testing.scenarios.dataset import Scenario, get_all, get_by_category, get_by_id

logger = structlog.get_logger()

# Enforce exact field names so parse_llm_response never sees invented names like reply_text.
# Mirrors what invoke_structured_gemini + GeneratorOutput does in production.
_EVAL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "visual_transcript": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sender": {"type": "string"},
                    "side": {"type": "string"},
                    "quoted_context": {"type": "string"},
                    "actual_new_message": {"type": "string"},
                    "is_reply_to_user": {"type": "boolean"},
                },
                "required": ["sender", "actual_new_message", "is_reply_to_user"],
            },
        },
        "analysis": {"type": "object"},
        "strategy": {"type": "object"},
        "replies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "strategy_label": {"type": "string"},
                    "is_recommended": {"type": "boolean"},
                    "coach_reasoning": {"type": "string"},
                },
                "required": ["text", "strategy_label", "is_recommended"],
            },
        },
    },
    "required": ["replies"],
}


@dataclass
class RunResult:
    scenario_id: str
    variant_id: str
    run_index: int
    replies: list[str]
    rule_report: rule_based.RuleReport
    judge_report: JudgeReport | None = None
    latency_ms: int = 0
    error: str | None = None


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    variant_id: str
    runs: list[RunResult] = field(default_factory=list)

    @property
    def avg_rule_score(self) -> float:
        scores = [r.rule_report.overall_score for r in self.runs if not r.error]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def avg_judge_score(self) -> float:
        scores = [
            r.judge_report.overall_score
            for r in self.runs
            if r.judge_report and not r.error
        ]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def avg_ai_isms(self) -> float:
        counts = [r.rule_report.ai_ism_count for r in self.runs if not r.error]
        return sum(counts) / len(counts) if counts else 0.0

    @property
    def avg_fork_rate(self) -> float:
        rates = [r.rule_report.fork_rate for r in self.runs if not r.error]
        return sum(rates) / len(rates) if rates else 0.0


@dataclass
class TestSuiteResult:
    variant_results: dict[str, list[ScenarioResult]] = field(default_factory=dict)

    def get_variant_summary(self, variant_id: str) -> dict:
        results = self.variant_results.get(variant_id, [])
        if not results:
            return {}
        return {
            "variant": variant_id,
            "scenarios_tested": len(results),
            "avg_rule_score": sum(r.avg_rule_score for r in results) / len(results),
            "avg_judge_score": sum(r.avg_judge_score for r in results) / len(results),
            "avg_ai_isms": sum(r.avg_ai_isms for r in results) / len(results),
            "avg_fork_rate": sum(r.avg_fork_rate for r in results) / len(results),
            "worst_scenario": min(results, key=lambda r: r.avg_rule_score).scenario_id,
            "best_scenario": max(results, key=lambda r: r.avg_rule_score).scenario_id,
        }


class TestRunner:
    def __init__(
        self, gemini_api_key: str | None = None, model: str | None = None
    ) -> None:
        api_key = gemini_api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.client = GeminiClient(api_key=api_key, default_model=self.model)

    async def run(
        self,
        variant_ids: list[str] | None = None,
        scenario_ids: list[str] | None = None,
        category: str | None = None,
        runs_per_combo: int = 3,
        use_judge: bool = False,
        judge_model: str | None = None,
    ) -> TestSuiteResult:
        """Run evaluation across variants × scenarios × N runs."""
        # Resolve scenarios
        if scenario_ids:
            scenarios = [s for s in get_all() if s.id in scenario_ids]
        elif category:
            scenarios = get_by_category(category)
        else:
            scenarios = get_all()

        # Resolve variants
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
                        use_judge=use_judge,
                        judge_model=judge_model,
                    )
                    scenario_result.runs.append(run_result)

                    # Rate limit: small delay between API calls
                    await asyncio.sleep(0.5)

                scenario_results.append(scenario_result)
                logger.info(
                    "scenario_complete",
                    scenario=scenario.id,
                    variant=variant_id,
                    avg_rule=f"{scenario_result.avg_rule_score:.2f}",
                    avg_judge=f"{scenario_result.avg_judge_score:.2f}",
                )

            suite_result.variant_results[variant_id] = scenario_results

        return suite_result

    async def _run_single(
        self,
        scenario: Scenario,
        variant_id: str,
        run_index: int,
        use_judge: bool,
        judge_model: str | None,
    ) -> RunResult:
        """Run a single scenario with a single variant."""
        try:
            # Build prompt
            payload = prompt_engine.build(
                direction=scenario.direction,
                variant_id=variant_id,
            )

            # For text-only testing (no real screenshot), use the description as user prompt
            user_prompt = (
                f"{payload.user_prompt}\n\n"
                f"[TESTING MODE - No screenshot available. Use this description instead:]\n"
                f"{scenario.screenshot_description}"
            )

            # Call LLM
            start = time.monotonic()
            raw = await self.client.vision_generate(
                system_prompt=payload.system_prompt,
                user_prompt=user_prompt,
                base64_images=[],  # No real image in test mode
                temperature=payload.temperature,
                model=self.model,
                max_output_tokens=(
                    payload.max_output_tokens
                    if hasattr(payload, "max_output_tokens")
                    else 2000
                ),
                response_schema=_EVAL_RESPONSE_SCHEMA,
            )
            latency_ms = int((time.monotonic() - start) * 1000)

            # Parse response
            parsed = parse_llm_response(raw)

            # Convert ReplyOption objects to strings for testing evaluators
            reply_strings = [r.text for r in parsed.replies]

            # Rule-based evaluation
            rule_report = rule_based.evaluate(reply_strings, scenario.quality_criteria)

            # LLM judge evaluation (optional)
            judge_report = None
            if use_judge:
                try:
                    judge_report = await judge_evaluate(
                        scenario=scenario,
                        replies=reply_strings,
                        judge_client=self.client,
                        judge_model=judge_model or self.model,
                    )
                except Exception as je:
                    logger.warning("judge_failed", scenario=scenario.id, error=str(je))

            return RunResult(
                scenario_id=scenario.id,
                variant_id=variant_id,
                run_index=run_index,
                replies=reply_strings,
                rule_report=rule_report,
                judge_report=judge_report,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error("run_failed", scenario=scenario.id, error=str(e))
            return RunResult(
                scenario_id=scenario.id,
                variant_id=variant_id,
                run_index=run_index,
                replies=[],
                rule_report=rule_based.RuleReport(overall_score=0.0),
                error=str(e),
            )

    async def close(self) -> None:
        await self.client.close()
