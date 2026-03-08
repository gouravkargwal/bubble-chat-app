"""Generate comparison reports from test suite results."""

from app.testing.runner import TestSuiteResult


def generate_report(result: TestSuiteResult) -> str:
    """Generate a formatted comparison report."""
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 80)
    lines.append("PROMPT VARIANT COMPARISON REPORT")
    lines.append("=" * 80)

    # Summary table
    summaries = []
    for variant_id in result.variant_results:
        summary = result.get_variant_summary(variant_id)
        if summary:
            summaries.append(summary)

    if not summaries:
        lines.append("No results to report.")
        return "\n".join(lines)

    # Sort by avg_rule_score descending
    summaries.sort(key=lambda s: s["avg_rule_score"], reverse=True)

    lines.append("")
    header = f"{'Variant':<25} {'Rule Score':>10} {'Judge Score':>12} {'AI-isms':>8} {'Fork Rate':>10} {'Scenarios':>10}"
    lines.append(header)
    lines.append("-" * 80)

    for s in summaries:
        judge_str = f"{s['avg_judge_score']:.1f}" if s["avg_judge_score"] > 0 else "N/A"
        lines.append(
            f"{s['variant']:<25} {s['avg_rule_score']:>10.2f} {judge_str:>12} "
            f"{s['avg_ai_isms']:>8.1f} {s['avg_fork_rate']:>9.0%} {s['scenarios_tested']:>10}"
        )

    lines.append("")

    # Per-variant breakdown
    for variant_id, scenario_results in result.variant_results.items():
        lines.append(f"\n{'─' * 80}")
        lines.append(f"VARIANT: {variant_id}")
        lines.append(f"{'─' * 80}")

        # Group by category
        categories: dict[str, list] = {}
        for sr in scenario_results:
            categories.setdefault(sr.category, []).append(sr)

        for category, results_in_cat in sorted(categories.items()):
            avg = sum(r.avg_rule_score for r in results_in_cat) / len(results_in_cat)
            lines.append(f"\n  {category} (avg: {avg:.2f})")

            for sr in sorted(results_in_cat, key=lambda r: r.avg_rule_score):
                status = "✓" if sr.avg_rule_score >= 0.7 else "✗"
                judge_str = f" | Judge: {sr.avg_judge_score:.1f}" if sr.avg_judge_score > 0 else ""
                lines.append(
                    f"    {status} {sr.scenario_id:<40} "
                    f"Rule: {sr.avg_rule_score:.2f}{judge_str} "
                    f"AI-isms: {sr.avg_ai_isms:.0f} Forks: {sr.avg_fork_rate:.0%}"
                )

                # Show sample replies from worst run
                if sr.runs and sr.avg_rule_score < 0.6:
                    worst_run = min(sr.runs, key=lambda r: r.rule_report.overall_score)
                    if worst_run.replies:
                        lines.append(f"      WORST REPLIES:")
                        for i, reply in enumerate(worst_run.replies[:2]):
                            lines.append(f"        {i+1}. {reply[:80]}{'...' if len(reply) > 80 else ''}")
                    if worst_run.rule_report.checks:
                        failed = [c for c in worst_run.rule_report.checks if not c.passed][:3]
                        for c in failed:
                            lines.append(f"        ⚠ {c.name}: {c.details}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    return "\n".join(lines)


def generate_json_report(result: TestSuiteResult) -> dict:
    """Generate a machine-readable JSON report."""
    report: dict = {"variants": {}}

    for variant_id in result.variant_results:
        summary = result.get_variant_summary(variant_id)
        scenario_details = []
        for sr in result.variant_results[variant_id]:
            detail = {
                "scenario_id": sr.scenario_id,
                "category": sr.category,
                "avg_rule_score": round(sr.avg_rule_score, 3),
                "avg_judge_score": round(sr.avg_judge_score, 3),
                "avg_ai_isms": round(sr.avg_ai_isms, 1),
                "avg_fork_rate": round(sr.avg_fork_rate, 3),
                "runs": len(sr.runs),
                "errors": sum(1 for r in sr.runs if r.error),
            }
            scenario_details.append(detail)

        report["variants"][variant_id] = {
            "summary": summary,
            "scenarios": scenario_details,
        }

    return report
