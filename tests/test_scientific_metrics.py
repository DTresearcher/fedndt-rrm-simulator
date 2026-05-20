from __future__ import annotations

import math

import pytest

from fedndt_rrm.scientific_metrics import (
    aggregate_alpha_fair_utility,
    alpha_fair_utility,
    communication_overhead_proxy,
    jain_fairness_index,
    latency_severity_summary,
    network_utility_score,
    percentile,
    prediction_error_summary,
)


def test_jain_fairness_index_perfect_fairness() -> None:
    assert jain_fairness_index([10, 10, 10, 10]) == pytest.approx(1.0)


def test_jain_fairness_index_unequal_allocation() -> None:
    fairness = jain_fairness_index([30, 10, 0])
    assert 0.0 < fairness < 1.0


def test_jain_fairness_index_empty_or_zero_vector() -> None:
    assert jain_fairness_index([]) == 0.0
    assert jain_fairness_index([0, 0, 0]) == 0.0


def test_percentile_uses_interpolation() -> None:
    assert percentile([10, 20, 30, 40], 50) == pytest.approx(25.0)
    assert percentile([10, 20, 30, 40], 95) == pytest.approx(38.5)


def test_latency_severity_summary() -> None:
    summary = latency_severity_summary(
        latencies_ms=[50, 100, 150, 250],
        sla_threshold_ms=100,
        severe_multiplier=2.0,
    )

    assert summary["avg_latency_ms"] == pytest.approx(137.5)
    assert summary["sla_violation_rate"] == pytest.approx(0.5)
    assert summary["severe_sla_violation_rate"] == pytest.approx(0.25)
    assert summary["avg_latency_excess_ms"] == pytest.approx(50.0)
    assert summary["max_latency_excess_ms"] == pytest.approx(150.0)
    assert summary["p99_latency_ms"] > summary["p95_latency_ms"]


def test_prediction_error_summary() -> None:
    summary = prediction_error_summary(
        actual_values=[100, 200, 300],
        predicted_values=[90, 210, 330],
    )

    assert summary["prediction_mae"] == pytest.approx((10 + 10 + 30) / 3)
    assert summary["prediction_rmse"] == pytest.approx(
        math.sqrt((100 + 100 + 900) / 3)
    )
    assert summary["prediction_mape"] > 0.0


def test_communication_overhead_proxy() -> None:
    overhead = communication_overhead_proxy(
        num_nodes=10,
        centralized_state_size_bytes=512,
        centralized_frequency_hz=2,
        participating_nodes=5,
        federated_model_update_size_bytes=128,
        federated_rounds=3,
    )

    assert overhead["centralized_overhead_bytes"] == pytest.approx(10240)
    assert overhead["federated_overhead_bytes"] == pytest.approx(1920)
    assert overhead["overhead_reduction_ratio"] == pytest.approx(0.8125)


def test_alpha_fair_utility_log_case() -> None:
    assert alpha_fair_utility(math.e, alpha=1.0) == pytest.approx(1.0)


def test_aggregate_alpha_fair_utility() -> None:
    utility = aggregate_alpha_fair_utility([1.0, math.e], alpha=1.0)
    assert utility == pytest.approx(1.0)


def test_network_utility_score_penalizes_latency_sla_and_overhead() -> None:
    clean_score = network_utility_score(
        throughputs=[10, 20, 30],
        mean_latency_excess_ms=0,
        sla_violation_rate=0,
        communication_overhead_bytes=0,
    )

    penalized_score = network_utility_score(
        throughputs=[10, 20, 30],
        mean_latency_excess_ms=10,
        sla_violation_rate=0.5,
        communication_overhead_bytes=1000,
    )

    assert penalized_score < clean_score
