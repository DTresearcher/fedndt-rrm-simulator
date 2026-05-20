from __future__ import annotations

from fedndt_rrm.config import load_config
from fedndt_rrm.scenario import generate_synthetic_telemetry


def test_generate_synthetic_telemetry_shape() -> None:
    config = load_config("configs/peak_traffic.yaml")
    telemetry, summary = generate_synthetic_telemetry(config)

    expected_rows = config.simulation.time_steps * config.network.num_users

    assert len(telemetry) == expected_rows
    assert summary.total_records == expected_rows
    assert telemetry["edge_node_id"].min() >= 0
    assert telemetry["edge_node_id"].max() < config.network.num_edge_nodes


def test_generated_telemetry_has_positive_values() -> None:
    config = load_config("configs/peak_traffic.yaml")
    telemetry, _ = generate_synthetic_telemetry(config)

    assert (telemetry["traffic_demand"] > 0).all()
    assert (telemetry["radio_quality"] > 0).all()
    assert (telemetry["throughput_potential"] > 0).all()
