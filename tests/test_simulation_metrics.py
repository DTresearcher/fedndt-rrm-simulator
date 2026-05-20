from __future__ import annotations

from fedndt_rrm.config import load_config
from fedndt_rrm.digital_twin import add_demand_predictions, build_local_digital_twins
from fedndt_rrm.incentive_engine import add_incentive_scores
from fedndt_rrm.metrics import evaluate_allocations
from fedndt_rrm.resource_allocator import STRATEGIES, allocate_resources
from fedndt_rrm.scenario import generate_synthetic_telemetry


def test_allocation_shape_and_strategy_count() -> None:
    config = load_config("configs/peak_traffic.yaml")
    telemetry, _ = generate_synthetic_telemetry(config)

    ndt_state = build_local_digital_twins(telemetry, config)
    ndt_state = add_demand_predictions(ndt_state, config)
    ndt_state = add_incentive_scores(ndt_state, config)

    allocations = allocate_resources(ndt_state, config)

    expected_rows = (
        config.simulation.time_steps
        * config.network.num_edge_nodes
        * len(STRATEGIES)
    )

    assert len(allocations) == expected_rows
    assert set(allocations["strategy"].unique()) == set(STRATEGIES)


def test_allocations_conserve_total_resources_per_step_and_strategy() -> None:
    config = load_config("configs/peak_traffic.yaml")
    telemetry, _ = generate_synthetic_telemetry(config)

    ndt_state = build_local_digital_twins(telemetry, config)
    ndt_state = add_demand_predictions(ndt_state, config)
    ndt_state = add_incentive_scores(ndt_state, config)

    allocations = allocate_resources(ndt_state, config)

    grouped = allocations.groupby(["time_step", "strategy"])[
        "allocated_resource_units"
    ].sum()

    for total in grouped:
        assert abs(total - config.network.total_resource_units) < 0.05


def test_evaluate_allocations_produces_summary_metrics() -> None:
    config = load_config("configs/peak_traffic.yaml")
    telemetry, _ = generate_synthetic_telemetry(config)

    ndt_state = build_local_digital_twins(telemetry, config)
    ndt_state = add_demand_predictions(ndt_state, config)
    ndt_state = add_incentive_scores(ndt_state, config)

    allocations = allocate_resources(ndt_state, config)
    per_step_metrics, summary_metrics = evaluate_allocations(
        ndt_state=ndt_state,
        allocations=allocations,
        config=config,
    )

    assert not per_step_metrics.empty
    assert not summary_metrics.empty
    assert set(summary_metrics["strategy"]) == set(STRATEGIES)
    assert (summary_metrics["avg_latency_ms"] > 0).all()
    assert summary_metrics["sla_violation_rate"].between(0, 1).all()
