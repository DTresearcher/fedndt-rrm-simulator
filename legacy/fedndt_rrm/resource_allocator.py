from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fedndt_rrm.config import ExperimentConfig


STRATEGIES = ("static", "greedy", "fedndt_incentive")


def _normalize_weights(weights: pd.Series, total_resource_units: float) -> pd.Series:
    positive_weights = weights.clip(lower=0.0)

    weight_sum = float(positive_weights.sum())
    if weight_sum <= 0:
        return pd.Series(
            np.full(len(weights), total_resource_units / len(weights)),
            index=weights.index,
        )

    return (positive_weights / weight_sum) * total_resource_units


def _add_delayed_greedy_signal(
    ndt_state: pd.DataFrame,
    config: ExperimentConfig,
) -> pd.DataFrame:
    ndt_state = ndt_state.copy()

    demand_signal_column = (
        "reported_total_demand"
        if "reported_total_demand" in ndt_state.columns
        else "total_demand"
    )

    delay = config.stress.greedy_observation_delay_steps if config.stress.enabled else 0

    frames: list[pd.DataFrame] = []

    for edge_node_id, node_df in ndt_state.groupby("edge_node_id", sort=True):
        node_df = node_df.sort_values("time_step").copy()

        delayed_signal = node_df[demand_signal_column].shift(delay)
        node_df["greedy_observed_demand"] = delayed_signal.fillna(
            node_df[demand_signal_column]
        )

        node_df["edge_node_id"] = int(edge_node_id)
        frames.append(node_df)

    return pd.concat(frames, ignore_index=True).sort_values(["time_step", "edge_node_id"])


def allocate_resources(
    ndt_state: pd.DataFrame,
    config: ExperimentConfig,
) -> pd.DataFrame:
    required_columns = {
        "time_step",
        "edge_node_id",
        "total_demand",
        "predicted_next_demand",
        "congestion_risk",
        "incentive_score",
    }

    missing_columns = required_columns.difference(ndt_state.columns)
    if missing_columns:
        raise ValueError(f"NDT state is missing required columns: {sorted(missing_columns)}")

    ndt_state = _add_delayed_greedy_signal(ndt_state, config)

    demand_signal_column = (
        "reported_total_demand"
        if "reported_total_demand" in ndt_state.columns
        else "total_demand"
    )

    records: list[dict[str, Any]] = []

    total_resource_units = config.network.total_resource_units
    num_edge_nodes = config.network.num_edge_nodes
    equal_share = total_resource_units / num_edge_nodes

    for time_step, step_df in ndt_state.groupby("time_step", sort=True):
        step_df = step_df.sort_values("edge_node_id").copy()

        strategy_weights = {
            "static": pd.Series(
                np.full(len(step_df), 1.0),
                index=step_df.index,
            ),
            "greedy": step_df["greedy_observed_demand"],
            "fedndt_incentive": (
                (0.65 * step_df["predicted_next_demand"])
                + (0.25 * step_df[demand_signal_column])
                + (0.10 * step_df["congestion_risk"] * equal_share)
            )
            * (0.60 + step_df["incentive_score"]),
        }

        for strategy, weights in strategy_weights.items():
            allocations = _normalize_weights(weights, total_resource_units)

            for idx, allocated_resource_units in allocations.items():
                row = step_df.loc[idx]

                records.append(
                    {
                        "time_step": int(time_step),
                        "edge_node_id": int(row["edge_node_id"]),
                        "strategy": strategy,
                        "allocated_resource_units": round(
                            float(allocated_resource_units),
                            4,
                        ),
                        "allocation_weight": round(float(weights.loc[idx]), 4),
                        "incentive_score": round(float(row["incentive_score"]), 4),
                    }
                )

    return pd.DataFrame.from_records(records)
