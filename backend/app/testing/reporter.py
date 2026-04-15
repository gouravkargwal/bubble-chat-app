"""Generate comparison reports from test suite results."""

from app.testing.runner import TestSuiteResult


def generate_report(result: TestSuiteResult) -> str:
    """Generate a formatted comparison report."""
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 90)
    lines.append("PROMPT VARIANT COMPARISON REPORT")
    lines.append("=" * 90)

    summaries = []
    for variant_id in result.variant_results:
        summary = result.get_variant_summary(variant_id)
        if summary:
            summaries.append(summary)

    if not summaries:
        lines.append("No results to report.")
        return "\n".join(lines)

    # Sort by avg_judge_score descending
    summaries.sort(key=lambda s: s["avg_judge_score"], reverse=True)

    lines.append("")
    header = (
        f"{'Variant':<25} {'Judge':>7} {'Specific':>9} {'Human':>7} {'Usable':>7} "
        f"{'Auditor':>8} {'Scenarios':>10}"
    )
    lines.append(header)
    lines.append("-" * 90)

    for s in summaries:
        lines.append(
            f"{s['variant']:<25} {s['avg_judge_score']:>7.1f} {s['avg_specificity']:>9.1f} "
            f"{s['avg_human_voice']:>7.1f} {s['avg_usability']:>7.1f} "
            f"{s['auditor_pass_rate']:>7.0%} {s['scenarios_tested']:>10}"
        )

    lines.append("")

    # Per-variant breakdown
    for variant_id, scenario_results in result.variant_results.items():
        lines.append(f"\n{'─' * 90}")
        lines.append(f"VARIANT: {variant_id}")
        lines.append(f"{'─' * 90}")

        # Group by category
        categories: dict[str, list] = {}
        for sr in scenario_results:
            categories.setdefault(sr.category, []).append(sr)

        for category, results_in_cat in sorted(categories.items()):
            avg = sum(r.avg_judge_score for r in results_in_cat) / len(results_in_cat)
            lines.append(f"\n  {category} (avg judge: {avg:.1f}/10)")

            for sr in sorted(results_in_cat, key=lambda r: r.avg_judge_score):
                status = "✓" if sr.avg_judge_score >= 6.0 else "✗"
                lines.append(
                    f"    {status} {sr.scenario_id:<42} "
                    f"Judge: {sr.avg_judge_score:.1f}  "
                    f"Spec: {sr.avg_specificity:.1f}  "
                    f"Human: {sr.avg_human_voice:.1f}  "
                    f"Use: {sr.avg_usability:.1f}  "
                    f"Auditor: {sr.auditor_pass_rate:.0%}"
                )

                # Show detail on weak scenarios
                if sr.avg_judge_score < 6.0 and sr.runs:
                    worst_run = min(
                        (r for r in sr.runs if r.judge_report),
                        key=lambda r: r.judge_report.overall_score,  # type: ignore[union-attr]
                        default=None,
                    )
                    if worst_run:
                        if worst_run.replies:
                            lines.append(f"      WORST REPLIES:")
                            for i, reply in enumerate(worst_run.replies[:2]):
                                lines.append(f"        {i+1}. {reply[:90]}{'...' if len(reply) > 90 else ''}")
                        if worst_run.judge_report and worst_run.judge_report.improvement_notes:
                            lines.append(f"        JUDGE: {worst_run.judge_report.improvement_notes[:200]}")
                        if worst_run.auditor_feedback:
                            lines.append(f"        AUDITOR: {worst_run.auditor_feedback[:160]}")

    lines.append("")
    lines.append("=" * 90)
    lines.append("END OF REPORT")
    lines.append("=" * 90)

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
                "avg_judge_score": round(sr.avg_judge_score, 2),
                "avg_specificity": round(sr.avg_specificity, 2),
                "avg_human_voice": round(sr.avg_human_voice, 2),
                "avg_usability": round(sr.avg_usability, 2),
                "auditor_pass_rate": round(sr.auditor_pass_rate, 3),
                "runs": len(sr.runs),
                "errors": sum(1 for r in sr.runs if r.error),
            }
            scenario_details.append(detail)

        report["variants"][variant_id] = {
            "summary": summary,
            "scenarios": scenario_details,
        }

    return report
