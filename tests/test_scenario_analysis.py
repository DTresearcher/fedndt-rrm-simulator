from __future__ import annotations

import pandas as pd
import pytest

from fedndt_rrm.scenario_analysis import (
    build_key_claim_summary,
    build_wide_improvement_table,
    compute_strategy_improvements,
    percentage_improvement_higher_is_better,
    percentage_improvement_lower_is_better,
)


def test_percentage_improvement_lower_is_better() -> None:
    assert percentage_improvement_lower_is_better(400, 300) == pytest.approx(25.0)


def test_percentage_improvement_higher_is_better() -> None:
    assert percentage_improvement_higher_is_better(0.8, 1.0) == pytest.approx(25.0)


def test_compute_strategy_improvements() -> None:
    comparison = pd.DataFrame(
        [
            {
                "scenario": "stress",
                "strategy": "static",
                "avg_latency_ms": 200.0,
                "p95_latency_ms": 500.0,
                "p99_latency_ms": 800.0,
                "sla_violation_rate": 0.40,
                "severe_sla_violation_rate": 0.30,
                "avg_latency_excess_ms": 100.0,
                "max_latency_excess_ms": 600.0,
                "resource_fairness_jain": 1.0,
                "throughput_fairness_jain": 0.90,
                "overhead_reduction_ratio": 0.0,
                "network_utility_score": 100.0,
            },
            {
                "scenario": "stress",
                "strategy": "greedy",
                "avg_latency_ms": 160.0,
                "p95_latency_ms": 400.0,
                "p99_latency_ms": 700.0,
                "sla_violation_rate": 0.50,
                "severe_sla_violation_rate": 0.35,
                "avg_latency_excess_ms": 80.0,
                "max_latency_excess_ms": 500.0,
                "resource_fairness_jain": 0.8,
                "throughput_fairness_jain": 0.75,
                "overhead_reduction_ratio": 0.0,
                "network_utility_score": 110.0,
            },
            {
                "scenario": "stress",
                "strategy": "fedndt_incentive",
                "avg_latency_ms": 120.0,
                "p95_latency_ms": 300.0,
                "p99_latency_ms": 350.0,
                "sla_violation_rate": 0.45,
                "severe_sla_violation_rate": 0.25,
                "avg_latency_excess_ms": 50.0,
                "max_latency_excess_ms": 250.0,
                "resource_fairness_jain": 0.85,
                "throughput_fairness_jain": 0.80,
                "overhead_reduction_ratio": 0.57,
                "network_utility_score": 115.0,
            },
        ]
    )

    improvements = compute_strategy_improvements(comparison)

    assert not improvements.empty

    greedy_p95 = improvements[
        (improvements["baseline_strategy"] == "greedy")
        & (improvements["metric"] == "p95_latency_ms")
    ].iloc[0]

    assert greedy_p95["improvement_pct"] == pytest.approx(25.0)

    static_p99 = improvements[
        (improvements["baseline_strategy"] == "static")
        & (improvements["metric"] == "p99_latency_ms")
    ].iloc[0]

    assert static_p99["improvement_pct"] == pytest.approx(56.25)


def test_build_wide_improvement_table() -> None:
    comparison = pd.DataFrame(
        [
            {
                "scenario": "stress",
                "strategy": "static",
                "avg_latency_ms": 200.0,
                "p95_latency_ms": 500.0,
                "p99_latency_ms": 800.0,
                "sla_violation_rate": 0.40,
                "severe_sla_violation_rate": 0.30,
                "avg_latency_excess_ms": 100.0,
                "max_latency_excess_ms": 600.0,
                "resource_fairness_jain": 1.0,
                "throughput_fairness_jain": 0.90,
                "overhead_reduction_ratio": 0.0,
                "network_utility_score": 100.0,
            },
            {
                "scenario": "stress",
                "strategy": "greedy",
                "avg_latency_ms": 160.0,
                "p95_latency_ms": 400.0,
                "p99_latency_ms": 700.0,
                "sla_violation_rate": 0.50,
                "severe_sla_violation_rate": 0.35,
                "avg_latency_excess_ms": 80.0,
                "max_latency_excess_ms": 500.0,
                "resource_fairness_jain": 0.8,
                "throughput_fairness_jain": 0.75,
                "overhead_reduction_ratio": 0.0,
                "network_utility_score": 110.0,
            },
            {
                "scenario": "stress",
                "strategy": "fedndt_incentive",
                "avg_latency_ms": 120.0,
                "p95_latency_ms": 300.0,
                "p99_latency_ms": 350.0,
                "sla_violation_rate": 0.45,
                "severe_sla_violation_rate": 0.25,
                "avg_latency_excess_ms": 50.0,
                "max_latency_excess_ms": 250.0,
                "resource_fairness_jain": 0.85,
                "throughput_fairness_jain": 0.80,
                "overhead_reduction_ratio": 0.57,
                "network_utility_score": 115.0,
            },
        ]
    )

    improvements = compute_strategy_improvements(comparison)
    wide = build_wide_improvement_table(improvements, baseline_strategy="greedy")

    assert "scenario" in wide.columns
    assert "p95_latency_improvement_pct" in wide.columns
    assert wide.iloc[0]["p95_latency_improvement_pct"] == pytest.approx(25.0)


def test_build_key_claim_summary() -> None:
    comparison = pd.DataFrame(
        [
            {
                "scenario": "stress",
                "strategy": "static",
                "avg_latency_ms": 200.0,
                "p95_latency_ms": 500.0,
                "p99_latency_ms": 800.0,
                "sla_violation_rate": 0.40,
                "severe_sla_violation_rate": 0.30,
                "avg_latency_excess_ms": 100.0,
                "max_latency_excess_ms": 600.0,
                "resource_fairness_jain": 1.0,
                "throughput_fairness_jain": 0.90,
                "overhead_reduction_ratio": 0.0,
                "network_utility_score": 100.0,
            },
            {
                "scenario": "stress",
                "strategy": "greedy",
                "avg_latency_ms": 160.0,
                "p95_latency_ms": 400.0,
                "p99_latency_ms": 700.0,
                "sla_violation_rate": 0.50,
                "severe_sla_violation_rate": 0.35,
                "avg_latency_excess_ms": 80.0,
                "max_latency_excess_ms": 500.0,
                "resource_fairness_jain": 0.8,
                "throughput_fairness_jain": 0.75,
                "overhead_reduction_ratio": 0.0,
                "network_utility_score": 110.0,
            },
            {
                "scenario": "stress",
                "strategy": "fedndt_incentive",
                "avg_latency_ms": 120.0,
                "p95_latency_ms": 300.0,
                "p99_latency_ms": 350.0,
                "sla_violation_rate": 0.45,
                "severe_sla_violation_rate": 0.25,
                "avg_latency_excess_ms": 50.0,
                "max_latency_excess_ms": 250.0,
                "resource_fairness_jain": 0.85,
                "throughput_fairness_jain": 0.80,
                "overhead_reduction_ratio": 0.57,
                "network_utility_score": 115.0,
            },
        ]
    )

    improvements = compute_strategy_improvements(comparison)
    claims = build_key_claim_summary(improvements)

    assert not claims.empty
    assert set(claims["claim_direction"]) == {"improved"}
