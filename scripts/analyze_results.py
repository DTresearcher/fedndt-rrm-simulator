from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def percentage_improvement(baseline: float, proposed: float) -> float:
    if baseline == 0:
        return 0.0
    return ((baseline - proposed) / baseline) * 100.0


def main() -> None:
    results_dir = Path("results")
    metrics_path = results_dir / "metrics.csv"
    summary_path = results_dir / "summary.json"

    metrics = pd.read_csv(metrics_path)

    with summary_path.open("r", encoding="utf-8") as file:
        summary = json.load(file)

    sla_threshold = float(summary["simulation"]["sla_latency_threshold_ms"])
    severe_threshold = 2.0 * sla_threshold

    metrics["latency_excess_ms"] = (metrics["latency_ms"] - sla_threshold).clip(lower=0)
    metrics["severe_sla_violation"] = (metrics["latency_ms"] > severe_threshold).astype(int)

    report = (
        metrics.groupby("strategy")
        .agg(
            avg_latency_ms=("latency_ms", "mean"),
            p95_latency_ms=("latency_ms", lambda x: x.quantile(0.95)),
            sla_violation_rate=("sla_violation", "mean"),
            severe_sla_violation_rate=("severe_sla_violation", "mean"),
            avg_latency_excess_ms=("latency_excess_ms", "mean"),
            avg_resource_utilization=("resource_utilization", "mean"),
            avg_effective_throughput=("effective_throughput", "mean"),
        )
        .reset_index()
    )

    numeric_cols = report.select_dtypes(include=["number"]).columns
    report[numeric_cols] = report[numeric_cols].round(4)

    proposed = report.loc[report["strategy"] == "fedndt_incentive"].iloc[0]

    comparisons = []
    for baseline_name in ["greedy", "static"]:
        baseline = report.loc[report["strategy"] == baseline_name].iloc[0]

        comparisons.append(
            {
                "baseline": baseline_name,
                "avg_latency_improvement_pct": round(
                    percentage_improvement(
                        float(baseline["avg_latency_ms"]),
                        float(proposed["avg_latency_ms"]),
                    ),
                    2,
                ),
                "p95_latency_improvement_pct": round(
                    percentage_improvement(
                        float(baseline["p95_latency_ms"]),
                        float(proposed["p95_latency_ms"]),
                    ),
                    2,
                ),
                "latency_excess_improvement_pct": round(
                    percentage_improvement(
                        float(baseline["avg_latency_excess_ms"]),
                        float(proposed["avg_latency_excess_ms"]),
                    ),
                    2,
                ),
            }
        )

    output = {
        "sla_threshold_ms": sla_threshold,
        "severe_sla_threshold_ms": severe_threshold,
        "strategy_report": report.to_dict(orient="records"),
        "fedndt_comparisons": comparisons,
    }

    report_path = results_dir / "analysis_report.json"
    table_path = results_dir / "analysis_report.csv"

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)

    report.to_csv(table_path, index=False)

    print("Analysis completed")
    print()
    print(report.to_string(index=False))
    print()
    print("FedNDT-Incentive improvements:")
    for item in comparisons:
        print(
            f"- vs {item['baseline']}: "
            f"avg latency {item['avg_latency_improvement_pct']}%, "
            f"p95 latency {item['p95_latency_improvement_pct']}%, "
            f"latency excess {item['latency_excess_improvement_pct']}%"
        )


if __name__ == "__main__":
    main()
