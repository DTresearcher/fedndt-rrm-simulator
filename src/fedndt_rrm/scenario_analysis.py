from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


TARGET_STRATEGY = "fedndt_incentive"
BASELINE_STRATEGIES = ("greedy", "static")

LOWER_IS_BETTER_METRICS = [
    "avg_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "sla_violation_rate",
    "severe_sla_violation_rate",
    "avg_latency_excess_ms",
    "max_latency_excess_ms",
]

HIGHER_IS_BETTER_METRICS = [
    "resource_fairness_jain",
    "throughput_fairness_jain",
    "overhead_reduction_ratio",
    "network_utility_score",
]


@dataclass(frozen=True)
class ImprovementResult:
    scenario: str
    baseline_strategy: str
    target_strategy: str
    metric: str
    baseline_value: float
    target_value: float
    absolute_delta: float
    improvement_pct: float


def percentage_improvement_lower_is_better(
    baseline_value: float,
    target_value: float,
) -> float:
    """Percentage improvement when a lower metric value is better.

    Example:
        baseline p95 = 400 ms
        target p95 = 300 ms
        improvement = (400 - 300) / 400 * 100 = 25%
    """
    baseline = float(baseline_value)
    target = float(target_value)

    if baseline == 0:
        return 0.0

    return ((baseline - target) / abs(baseline)) * 100.0


def percentage_improvement_higher_is_better(
    baseline_value: float,
    target_value: float,
) -> float:
    """Percentage improvement when a higher metric value is better."""
    baseline = float(baseline_value)
    target = float(target_value)

    if baseline == 0:
        return 0.0

    return ((target - baseline) / abs(baseline)) * 100.0


def _get_strategy_row(
    scenario_frame: pd.DataFrame,
    strategy: str,
) -> pd.Series:
    rows = scenario_frame[scenario_frame["strategy"] == strategy]
    if rows.empty:
        msg = f"Strategy '{strategy}' not found in scenario frame."
        raise ValueError(msg)

    if len(rows) > 1:
        msg = f"Strategy '{strategy}' appears more than once in scenario frame."
        raise ValueError(msg)

    return rows.iloc[0]


def compute_strategy_improvements(
    comparison: pd.DataFrame,
    *,
    target_strategy: str = TARGET_STRATEGY,
    baseline_strategies: tuple[str, ...] = BASELINE_STRATEGIES,
) -> pd.DataFrame:
    """Compute target-vs-baseline improvements for each scenario.

    Lower-is-better metrics are reported as percentage reduction.
    Higher-is-better metrics are reported as percentage gain.
    """
    required_columns = {"scenario", "strategy"}
    missing_columns = required_columns.difference(comparison.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    results: list[ImprovementResult] = []

    for scenario, scenario_frame in comparison.groupby("scenario", sort=False):
        target_row = _get_strategy_row(scenario_frame, target_strategy)

        for baseline_strategy in baseline_strategies:
            baseline_row = _get_strategy_row(scenario_frame, baseline_strategy)

            for metric in LOWER_IS_BETTER_METRICS:
                if metric not in comparison.columns:
                    continue

                baseline_value = float(baseline_row[metric])
                target_value = float(target_row[metric])
                improvement_pct = percentage_improvement_lower_is_better(
                    baseline_value=baseline_value,
                    target_value=target_value,
                )

                results.append(
                    ImprovementResult(
                        scenario=str(scenario),
                        baseline_strategy=baseline_strategy,
                        target_strategy=target_strategy,
                        metric=metric,
                        baseline_value=baseline_value,
                        target_value=target_value,
                        absolute_delta=target_value - baseline_value,
                        improvement_pct=improvement_pct,
                    )
                )

            for metric in HIGHER_IS_BETTER_METRICS:
                if metric not in comparison.columns:
                    continue

                baseline_value = float(baseline_row[metric])
                target_value = float(target_row[metric])
                improvement_pct = percentage_improvement_higher_is_better(
                    baseline_value=baseline_value,
                    target_value=target_value,
                )

                results.append(
                    ImprovementResult(
                        scenario=str(scenario),
                        baseline_strategy=baseline_strategy,
                        target_strategy=target_strategy,
                        metric=metric,
                        baseline_value=baseline_value,
                        target_value=target_value,
                        absolute_delta=target_value - baseline_value,
                        improvement_pct=improvement_pct,
                    )
                )

    output = pd.DataFrame([result.__dict__ for result in results])
    numeric_columns = output.select_dtypes(include=["number"]).columns
    output[numeric_columns] = output[numeric_columns].round(4)

    return output


def build_wide_improvement_table(
    improvements: pd.DataFrame,
    *,
    baseline_strategy: str,
) -> pd.DataFrame:
    """Create a scenario-level table for one baseline strategy."""
    baseline_frame = improvements[
        improvements["baseline_strategy"] == baseline_strategy
    ].copy()

    if baseline_frame.empty:
        msg = f"No improvement rows found for baseline '{baseline_strategy}'."
        raise ValueError(msg)

    selected_metrics = [
        "avg_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "sla_violation_rate",
        "severe_sla_violation_rate",
        "avg_latency_excess_ms",
        "max_latency_excess_ms",
        "resource_fairness_jain",
        "throughput_fairness_jain",
        "overhead_reduction_ratio",
    ]

    baseline_frame = baseline_frame[
        baseline_frame["metric"].isin(selected_metrics)
    ].copy()

    wide = baseline_frame.pivot_table(
        index="scenario",
        columns="metric",
        values="improvement_pct",
        aggfunc="first",
    ).reset_index()

    rename_map = {
        "avg_latency_ms": "avg_latency_improvement_pct",
        "p95_latency_ms": "p95_latency_improvement_pct",
        "p99_latency_ms": "p99_latency_improvement_pct",
        "sla_violation_rate": "sla_violation_improvement_pct",
        "severe_sla_violation_rate": "severe_sla_improvement_pct",
        "avg_latency_excess_ms": "avg_latency_excess_improvement_pct",
        "max_latency_excess_ms": "max_latency_excess_improvement_pct",
        "resource_fairness_jain": "resource_fairness_gain_pct",
        "throughput_fairness_jain": "throughput_fairness_gain_pct",
        "overhead_reduction_ratio": "overhead_reduction_gain_pct",
    }

    wide = wide.rename(columns=rename_map)
    numeric_columns = wide.select_dtypes(include=["number"]).columns
    wide[numeric_columns] = wide[numeric_columns].round(2)

    return wide


def build_key_claim_summary(improvements: pd.DataFrame) -> pd.DataFrame:
    """Build conservative claim-support rows for paper discussion.

    The table focuses on latency-severity metrics because raw SLA violation
    rate can be misleading when a strategy has fewer violations but much worse
    tail latency or much larger violation excess.
    """
    claim_metrics = [
        "avg_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "avg_latency_excess_ms",
        "max_latency_excess_ms",
    ]

    claim_frame = improvements[
        improvements["metric"].isin(claim_metrics)
    ].copy()

    claim_frame["claim_direction"] = claim_frame["improvement_pct"].apply(
        lambda value: "improved" if value > 0 else "worse_or_equal"
    )

    claim_frame = claim_frame.sort_values(
        by=["scenario", "baseline_strategy", "metric"]
    )

    numeric_columns = claim_frame.select_dtypes(include=["number"]).columns
    claim_frame[numeric_columns] = claim_frame[numeric_columns].round(4)

    return claim_frame
