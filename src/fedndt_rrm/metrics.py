from __future__ import annotations

import numpy as np
import pandas as pd

from fedndt_rrm.config import ExperimentConfig


def evaluate_allocations(
    ndt_state: pd.DataFrame,
    allocations: pd.DataFrame,
    config: ExperimentConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_ndt_columns = {
        "time_step",
        "edge_node_id",
        "total_demand",
        "avg_radio_quality",
        "quality_risk",
        "congestion_risk",
        "prediction_error_abs",
    }

    required_allocation_columns = {
        "time_step",
        "edge_node_id",
        "strategy",
        "allocated_resource_units",
        "incentive_score",
    }

    missing_ndt = required_ndt_columns.difference(ndt_state.columns)
    missing_alloc = required_allocation_columns.difference(allocations.columns)

    if missing_ndt:
        raise ValueError(f"NDT state is missing required columns: {sorted(missing_ndt)}")

    if missing_alloc:
        raise ValueError(
            f"Allocations are missing required columns: {sorted(missing_alloc)}"
        )

    merged = allocations.merge(
        ndt_state,
        on=["time_step", "edge_node_id"],
        how="left",
        suffixes=("", "_ndt"),
    )

    capacity = merged["allocated_resource_units"].replace(0, 1e-9)
    load_ratio = merged["total_demand"] / capacity

    merged["load_ratio"] = load_ratio.round(4)
    merged["resource_utilization"] = load_ratio.clip(0.0, 1.0).round(4)

    overload_ratio = (load_ratio - 1.0).clip(lower=0.0)

    queue_delay_ms = (
        config.network.base_latency_ms
        * 2.2
        * np.power(load_ratio.clip(lower=0.0), 2)
    )

    radio_penalty_ms = 15.0 * merged["quality_risk"]
    congestion_penalty_ms = 25.0 * overload_ratio

    merged["latency_ms"] = (
        config.network.base_latency_ms
        + queue_delay_ms
        + radio_penalty_ms
        + congestion_penalty_ms
    ).round(4)

    merged["sla_violation"] = (
        merged["latency_ms"] > config.network.sla_latency_threshold_ms
    ).astype(int)

    merged["effective_throughput"] = (
        merged["allocated_resource_units"]
        * (1.0 - 0.35 * merged["quality_risk"])
        * (1.0 - 0.50 * overload_ratio.clip(upper=1.0))
    ).clip(lower=0.0).round(4)

    per_step_metrics = merged[
        [
            "time_step",
            "edge_node_id",
            "strategy",
            "allocated_resource_units",
            "total_demand",
            "load_ratio",
            "resource_utilization",
            "latency_ms",
            "effective_throughput",
            "sla_violation",
            "congestion_risk",
            "prediction_error_abs",
            "incentive_score",
        ]
    ].copy()

    summary_metrics = (
        per_step_metrics.groupby("strategy")
        .agg(
            avg_latency_ms=("latency_ms", "mean"),
            p95_latency_ms=("latency_ms", lambda x: x.quantile(0.95)),
            sla_violation_rate=("sla_violation", "mean"),
            avg_resource_utilization=("resource_utilization", "mean"),
            avg_effective_throughput=("effective_throughput", "mean"),
            avg_prediction_error_abs=("prediction_error_abs", "mean"),
            avg_incentive_score=("incentive_score", "mean"),
        )
        .reset_index()
    )

    numeric_columns = summary_metrics.select_dtypes(include=["number"]).columns
    summary_metrics[numeric_columns] = summary_metrics[numeric_columns].round(4)

    return per_step_metrics, summary_metrics
