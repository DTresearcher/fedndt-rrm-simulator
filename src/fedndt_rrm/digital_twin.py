from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fedndt_rrm.config import ExperimentConfig


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _safe_mean(series: pd.Series, default: float = 0.0) -> float:
    if series.empty:
        return default
    return float(series.mean())


def _apply_unreliable_reporting(
    ndt_state: pd.DataFrame,
    config: ExperimentConfig,
) -> pd.DataFrame:
    ndt_state = ndt_state.copy()
    ndt_state["reported_total_demand"] = ndt_state["total_demand"]
    ndt_state["update_available"] = 1
    ndt_state["report_noise_factor"] = 1.0

    if not config.stress.enabled:
        ndt_state["reporting_error_abs"] = 0.0
        return ndt_state

    unreliable_node = config.stress.unreliable_edge_node_id

    if unreliable_node >= config.network.num_edge_nodes:
        ndt_state["reporting_error_abs"] = 0.0
        return ndt_state

    rng = np.random.default_rng(config.simulation.random_seed + 999)
    node_mask = ndt_state["edge_node_id"] == unreliable_node
    node_indexes = ndt_state.loc[node_mask].sort_values("time_step").index

    last_reported = None

    for idx in node_indexes:
        actual_demand = float(ndt_state.at[idx, "total_demand"])

        if last_reported is None:
            last_reported = actual_demand

        if rng.random() < config.stress.stale_update_probability:
            ndt_state.at[idx, "reported_total_demand"] = last_reported
            ndt_state.at[idx, "update_available"] = 0
            ndt_state.at[idx, "report_noise_factor"] = 0.0
            continue

        if rng.random() < config.stress.report_noise_probability:
            factor = float(
                np.clip(
                    rng.normal(loc=1.0, scale=config.stress.report_noise_std),
                    0.30,
                    1.70,
                )
            )
            reported = actual_demand * factor
            ndt_state.at[idx, "reported_total_demand"] = reported
            ndt_state.at[idx, "report_noise_factor"] = factor
            last_reported = reported
        else:
            ndt_state.at[idx, "reported_total_demand"] = actual_demand
            ndt_state.at[idx, "report_noise_factor"] = 1.0
            last_reported = actual_demand

    ndt_state["reporting_error_abs"] = (
        ndt_state["total_demand"] - ndt_state["reported_total_demand"]
    ).abs()

    for column in ["reported_total_demand", "report_noise_factor", "reporting_error_abs"]:
        ndt_state[column] = ndt_state[column].round(4)

    ndt_state["update_available"] = ndt_state["update_available"].astype(int)

    return ndt_state


def build_local_digital_twins(
    telemetry: pd.DataFrame,
    config: ExperimentConfig,
) -> pd.DataFrame:
    required_columns = {
        "time_step",
        "user_id",
        "edge_node_id",
        "traffic_demand",
        "radio_quality",
        "throughput_potential",
    }

    missing_columns = required_columns.difference(telemetry.columns)
    if missing_columns:
        raise ValueError(f"Telemetry is missing required columns: {sorted(missing_columns)}")

    records: list[dict[str, Any]] = []

    nominal_node_capacity = config.network.total_resource_units / config.network.num_edge_nodes
    max_expected_quality = max(config.radio.base_quality, 1.0)

    grouped = telemetry.groupby(["time_step", "edge_node_id"], sort=True)

    for (time_step, edge_node_id), group in grouped:
        active_users = int(group["user_id"].nunique())
        total_demand = float(group["traffic_demand"].sum())
        avg_demand_per_user = float(group["traffic_demand"].mean())
        avg_radio_quality = _safe_mean(group["radio_quality"])
        avg_throughput_potential = _safe_mean(group["throughput_potential"])

        demand_pressure = total_demand / max(nominal_node_capacity, 1e-9)
        quality_risk = 1.0 - (avg_radio_quality / max_expected_quality)
        congestion_risk = _clip01((0.75 * demand_pressure) + (0.25 * quality_risk))

        records.append(
            {
                "time_step": int(time_step),
                "edge_node_id": int(edge_node_id),
                "active_users": active_users,
                "total_demand": round(total_demand, 4),
                "avg_demand_per_user": round(avg_demand_per_user, 4),
                "avg_radio_quality": round(avg_radio_quality, 4),
                "avg_throughput_potential": round(avg_throughput_potential, 4),
                "nominal_node_capacity": round(nominal_node_capacity, 4),
                "demand_pressure": round(demand_pressure, 4),
                "quality_risk": round(_clip01(quality_risk), 4),
                "congestion_risk": round(congestion_risk, 4),
            }
        )

    ndt_state = pd.DataFrame.from_records(records)

    full_index = pd.MultiIndex.from_product(
        [range(config.simulation.time_steps), range(config.network.num_edge_nodes)],
        names=["time_step", "edge_node_id"],
    )

    ndt_state = (
        ndt_state.set_index(["time_step", "edge_node_id"])
        .reindex(full_index)
        .reset_index()
    )

    fill_values = {
        "active_users": 0,
        "total_demand": 0.0,
        "avg_demand_per_user": 0.0,
        "avg_radio_quality": 0.0,
        "avg_throughput_potential": 0.0,
        "nominal_node_capacity": nominal_node_capacity,
        "demand_pressure": 0.0,
        "quality_risk": 1.0,
        "congestion_risk": 0.0,
    }

    ndt_state = ndt_state.fillna(fill_values)
    ndt_state["active_users"] = ndt_state["active_users"].astype(int)

    return _apply_unreliable_reporting(ndt_state, config)


def add_demand_predictions(
    ndt_state: pd.DataFrame,
    config: ExperimentConfig,
) -> pd.DataFrame:
    required_columns = {"time_step", "edge_node_id", "total_demand"}

    missing_columns = required_columns.difference(ndt_state.columns)
    if missing_columns:
        raise ValueError(f"NDT state is missing required columns: {sorted(missing_columns)}")

    demand_signal_column = (
        "reported_total_demand"
        if "reported_total_demand" in ndt_state.columns
        else "total_demand"
    )

    history_window = config.federated.history_window
    smoothing = config.federated.prediction_smoothing

    frames: list[pd.DataFrame] = []

    for edge_node_id, node_df in ndt_state.groupby("edge_node_id", sort=True):
        node_df = node_df.sort_values("time_step").copy()

        demand_signal = node_df[demand_signal_column]

        rolling_prediction = (
            demand_signal.rolling(window=history_window, min_periods=1).mean().shift(1)
        )

        fallback_prediction = demand_signal.expanding(min_periods=1).mean()

        node_df["predicted_next_demand"] = rolling_prediction.fillna(fallback_prediction)

        node_df["predicted_next_demand"] = (
            smoothing * node_df["predicted_next_demand"]
            + (1.0 - smoothing) * demand_signal
        )

        node_df["prediction_error_abs"] = (
            node_df["total_demand"] - node_df["predicted_next_demand"]
        ).abs()

        node_df["edge_node_id"] = int(edge_node_id)

        frames.append(node_df)

    predicted_state = pd.concat(frames, ignore_index=True)
    predicted_state = predicted_state.sort_values(["time_step", "edge_node_id"])

    predicted_state["predicted_next_demand"] = predicted_state[
        "predicted_next_demand"
    ].round(4)

    predicted_state["prediction_error_abs"] = predicted_state[
        "prediction_error_abs"
    ].round(4)

    return predicted_state
