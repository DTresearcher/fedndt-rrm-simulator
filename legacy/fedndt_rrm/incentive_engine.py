from __future__ import annotations

import numpy as np
import pandas as pd

from fedndt_rrm.config import ExperimentConfig


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def add_incentive_scores(
    ndt_state: pd.DataFrame,
    config: ExperimentConfig,
) -> pd.DataFrame:
    required_columns = {
        "time_step",
        "edge_node_id",
        "total_demand",
        "prediction_error_abs",
        "active_users",
    }

    missing_columns = required_columns.difference(ndt_state.columns)
    if missing_columns:
        raise ValueError(f"NDT state is missing required columns: {sorted(missing_columns)}")

    demand_signal_column = (
        "reported_total_demand"
        if "reported_total_demand" in ndt_state.columns
        else "total_demand"
    )

    update_available_column = (
        "update_available" if "update_available" in ndt_state.columns else None
    )

    frames: list[pd.DataFrame] = []
    max_active_users = max(float(ndt_state["active_users"].max()), 1.0)

    for edge_node_id, node_df in ndt_state.groupby("edge_node_id", sort=True):
        node_df = node_df.sort_values("time_step").copy()

        demand_denominator = node_df["total_demand"].replace(0, 1e-9)
        prediction_accuracy = 1.0 - (node_df["prediction_error_abs"] / demand_denominator)
        node_df["prediction_accuracy_score"] = prediction_accuracy.clip(0.0, 1.0)

        demand_signal = node_df[demand_signal_column]

        rolling_std = (
            demand_signal.rolling(window=config.federated.history_window, min_periods=2)
            .std()
            .fillna(0.0)
        )

        rolling_mean = (
            demand_signal.rolling(window=config.federated.history_window, min_periods=1)
            .mean()
            .replace(0, 1e-9)
        )

        node_df["consistency_score"] = (1.0 - (rolling_std / rolling_mean)).clip(0.0, 1.0)

        if update_available_column:
            node_df["freshness_score"] = node_df[update_available_column].clip(0.0, 1.0)
        else:
            node_df["freshness_score"] = 1.0

        node_df["fairness_score"] = (node_df["active_users"] / max_active_users).clip(
            0.0,
            1.0,
        )

        if config.incentive.enabled:
            node_df["incentive_score"] = (
                config.incentive.freshness_weight * node_df["freshness_score"]
                + config.incentive.accuracy_weight * node_df["prediction_accuracy_score"]
                + config.incentive.consistency_weight * node_df["consistency_score"]
                + config.incentive.fairness_weight * node_df["fairness_score"]
            )
        else:
            node_df["incentive_score"] = 1.0

        node_df["incentive_score"] = node_df["incentive_score"].apply(_clip01).round(4)
        node_df["edge_node_id"] = int(edge_node_id)

        frames.append(node_df)

    scored_state = pd.concat(frames, ignore_index=True)
    return scored_state.sort_values(["time_step", "edge_node_id"]).reset_index(drop=True)
