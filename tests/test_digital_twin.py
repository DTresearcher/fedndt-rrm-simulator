from __future__ import annotations

from fedndt_rrm.config import load_config
from fedndt_rrm.digital_twin import add_demand_predictions, build_local_digital_twins
from fedndt_rrm.scenario import generate_synthetic_telemetry


def test_build_local_digital_twins_shape() -> None:
    config = load_config("configs/peak_traffic.yaml")
    telemetry, _ = generate_synthetic_telemetry(config)

    ndt_state = build_local_digital_twins(telemetry, config)

    expected_rows = config.simulation.time_steps * config.network.num_edge_nodes

    assert len(ndt_state) == expected_rows
    assert ndt_state["edge_node_id"].min() >= 0
    assert ndt_state["edge_node_id"].max() < config.network.num_edge_nodes


def test_ndt_state_risk_values_are_bounded() -> None:
    config = load_config("configs/peak_traffic.yaml")
    telemetry, _ = generate_synthetic_telemetry(config)

    ndt_state = build_local_digital_twins(telemetry, config)

    assert ndt_state["congestion_risk"].between(0, 1).all()
    assert ndt_state["quality_risk"].between(0, 1).all()


def test_add_demand_predictions() -> None:
    config = load_config("configs/peak_traffic.yaml")
    telemetry, _ = generate_synthetic_telemetry(config)

    ndt_state = build_local_digital_twins(telemetry, config)
    predicted_state = add_demand_predictions(ndt_state, config)

    assert "predicted_next_demand" in predicted_state.columns
    assert "prediction_error_abs" in predicted_state.columns
    assert predicted_state["predicted_next_demand"].notna().all()
    assert predicted_state["prediction_error_abs"].notna().all()
