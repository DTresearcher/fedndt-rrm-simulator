from __future__ import annotations

from fedndt_rrm.config import load_config
from fedndt_rrm.digital_twin import add_demand_predictions, build_local_digital_twins
from fedndt_rrm.incentive_engine import add_incentive_scores
from fedndt_rrm.metrics import evaluate_allocations
from fedndt_rrm.resource_allocator import STRATEGIES, allocate_resources
from fedndt_rrm.scenario import generate_synthetic_telemetry


EXPECTED_PER_STEP_COLUMNS = {
    "time_step",
    "edge_node_id",
    "strategy",
    "allocated_resource_units",
    "total_demand",
    "predicted_demand",
    "load_ratio",
    "resource_utilization",
    "latency_ms",
    "latency_excess_ms",
    "effective_throughput",
    "resource_fairness_jain",
    "throughput_fairness_jain",
    "sla_violation",
    "severe_sla_violation",
    "congestion_risk",
    "prediction_error_abs",
    "incentive_score",
}

EXPECTED_SUMMARY_COLUMNS = {
    "strategy",
    "avg_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "sla_violation_rate",
    "severe_sla_violation_rate",
    "avg_latency_excess_ms",
    "max_latency_excess_ms",
    "avg_resource_utilization",
    "avg_effective_throughput",
    "resource_fairness_jain",
    "throughput_fairness_jain",
    "avg_prediction_error_abs",
    "prediction_mae",
    "prediction_rmse",
    "prediction_mape",
    "avg_incentive_score",
    "centralized_overhead_bytes",
    "federated_overhead_bytes",
    "communication_overhead_bytes",
    "overhead_reduction_ratio",
    "network_utility_score",
}


def _build_simulation_outputs():
    config = load_config("configs/peak_traffic.yaml")
    telemetry, _ = generate_synthetic_telemetry(config)

    ndt_state = build_local_digital_twins(telemetry, config)
    ndt_state = add_demand_predictions(ndt_state, config)
    ndt_state = add_incentive_scores(ndt_state, config)

    allocations = allocate_resources(ndt_state, config)

    return config, telemetry, ndt_state, allocations


def test_allocation_shape_and_strategy_count() -> None:
    config, _, _, allocations = _build_simulation_outputs()

    expected_rows = (
        config.simulation.time_steps
        * config.network.num_edge_nodes
        * len(STRATEGIES)
    )

    assert len(allocations) == expected_rows
    assert set(allocations["strategy"].unique()) == set(STRATEGIES)


def test_allocations_conserve_total_resources_per_step_and_strategy() -> None:
    config, _, _, allocations = _build_simulation_outputs()

    grouped = allocations.groupby(["time_step", "strategy"])[
        "allocated_resource_units"
    ].sum()

    for total in grouped:
        assert abs(total - config.network.total_resource_units) < 0.05


def test_evaluate_allocations_produces_summary_metrics() -> None:
    config, _, ndt_state, allocations = _build_simulation_outputs()

    per_step_metrics, summary_metrics = evaluate_allocations(
        ndt_state=ndt_state,
        allocations=allocations,
        config=config,
    )

    assert not per_step_metrics.empty
    assert not summary_metrics.empty
    assert EXPECTED_PER_STEP_COLUMNS.issubset(per_step_metrics.columns)
    assert EXPECTED_SUMMARY_COLUMNS.issubset(summary_metrics.columns)
    assert set(summary_metrics["strategy"]) == set(STRATEGIES)

    assert (summary_metrics["avg_latency_ms"] > 0).all()
    assert summary_metrics["sla_violation_rate"].between(0, 1).all()
    assert summary_metrics["severe_sla_violation_rate"].between(0, 1).all()

    assert (
        summary_metrics["p99_latency_ms"] >= summary_metrics["p95_latency_ms"]
    ).all()

    assert summary_metrics["resource_fairness_jain"].between(0, 1).all()
    assert summary_metrics["throughput_fairness_jain"].between(0, 1).all()

    assert (summary_metrics["prediction_mae"] >= 0).all()
    assert (summary_metrics["prediction_rmse"] >= 0).all()
    assert (summary_metrics["prediction_mape"] >= 0).all()

    assert (summary_metrics["centralized_overhead_bytes"] >= 0).all()
    assert (summary_metrics["federated_overhead_bytes"] >= 0).all()
    assert (summary_metrics["communication_overhead_bytes"] >= 0).all()
