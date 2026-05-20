from __future__ import annotations

import math

import numpy as np
import pandas as pd

from fedndt_rrm.config import ExperimentConfig
from fedndt_rrm.scientific_metrics import (
    communication_overhead_proxy,
    jain_fairness_index,
    latency_severity_summary,
    network_utility_score,
    prediction_error_summary,
)


_EPSILON = 1e-9

# Lightweight network-level overhead assumptions.
# These are proxy values, not measured packet traces.
CENTRALIZED_STATE_FEATURE_COUNT = 7
LIGHTWEIGHT_FEDAVG_PARAMETER_COUNT = 3
FLOAT_PARAMETER_SIZE_BYTES = 8.0


def _prediction_summary_from_frame(frame: pd.DataFrame) -> dict[str, float]:
    """Compute prediction errors from deterministic simulation columns."""
    if "predicted_demand" in frame.columns and frame["predicted_demand"].notna().any():
        return prediction_error_summary(
            actual_values=frame["total_demand"].to_list(),
            predicted_values=frame["predicted_demand"].to_list(),
        )

    absolute_errors = [
        float(value)
        for value in frame["prediction_error_abs"].to_list()
        if math.isfinite(float(value))
    ]

    if not absolute_errors:
        return {
            "prediction_mae": 0.0,
            "prediction_rmse": 0.0,
            "prediction_mape": 0.0,
        }

    actual_values = [
        float(value)
        for value in frame["total_demand"].to_list()
        if math.isfinite(float(value))
    ]

    squared_errors = [error**2 for error in absolute_errors]
    percentage_errors = [
        error / max(abs(actual), _EPSILON)
        for error, actual in zip(absolute_errors, actual_values, strict=False)
    ]

    return {
        "prediction_mae": sum(absolute_errors) / len(absolute_errors),
        "prediction_rmse": math.sqrt(sum(squared_errors) / len(squared_errors)),
        "prediction_mape": sum(percentage_errors) / len(percentage_errors),
    }


def _communication_overhead_by_strategy(
    strategy: str,
    config: ExperimentConfig,
) -> dict[str, float]:
    """Return deterministic communication-overhead proxy per strategy."""
    num_nodes = max(0, int(config.network.num_edge_nodes))
    update_count = max(1, int(config.simulation.time_steps))

    centralized_state_size_bytes = (
        CENTRALIZED_STATE_FEATURE_COUNT * FLOAT_PARAMETER_SIZE_BYTES
    )
    fedavg_model_update_size_bytes = (
        LIGHTWEIGHT_FEDAVG_PARAMETER_COUNT * FLOAT_PARAMETER_SIZE_BYTES
    )

    centralized_total_bytes = (
        num_nodes * centralized_state_size_bytes * update_count
    )

    if strategy == "fedndt_incentive":
        overhead = communication_overhead_proxy(
            num_nodes=num_nodes,
            centralized_state_size_bytes=centralized_state_size_bytes,
            centralized_frequency_hz=update_count,
            participating_nodes=num_nodes,
            federated_model_update_size_bytes=fedavg_model_update_size_bytes,
            federated_rounds=update_count,
        )
        overhead["communication_overhead_bytes"] = overhead[
            "federated_overhead_bytes"
        ]
        return overhead

    if strategy == "greedy":
        return {
            "centralized_overhead_bytes": centralized_total_bytes,
            "federated_overhead_bytes": 0.0,
            "overhead_reduction_ratio": 0.0,
            "communication_overhead_bytes": centralized_total_bytes,
        }

    return {
        "centralized_overhead_bytes": 0.0,
        "federated_overhead_bytes": 0.0,
        "overhead_reduction_ratio": 0.0,
        "communication_overhead_bytes": 0.0,
    }


def _build_summary_metrics(
    per_step_metrics: pd.DataFrame,
    config: ExperimentConfig,
) -> pd.DataFrame:
    """Build strategy-level summary metrics."""
    summary_rows: list[dict[str, float | str]] = []
    sla_threshold = config.network.sla_latency_threshold_ms

    for strategy, strategy_frame in per_step_metrics.groupby("strategy", sort=False):
        latency_summary = latency_severity_summary(
            latencies_ms=strategy_frame["latency_ms"].to_list(),
            sla_threshold_ms=sla_threshold,
            severe_multiplier=2.0,
        )
        prediction_summary = _prediction_summary_from_frame(strategy_frame)
        overhead_summary = _communication_overhead_by_strategy(
            strategy=str(strategy),
            config=config,
        )

        utility_score = network_utility_score(
            throughputs=strategy_frame["effective_throughput"].to_list(),
            mean_latency_excess_ms=latency_summary["avg_latency_excess_ms"],
            sla_violation_rate=latency_summary["sla_violation_rate"],
            communication_overhead_bytes=overhead_summary[
                "communication_overhead_bytes"
            ],
        )

        summary_rows.append(
            {
                "strategy": str(strategy),
                "avg_latency_ms": latency_summary["avg_latency_ms"],
                "p95_latency_ms": latency_summary["p95_latency_ms"],
                "p99_latency_ms": latency_summary["p99_latency_ms"],
                "sla_violation_rate": latency_summary["sla_violation_rate"],
                "severe_sla_violation_rate": latency_summary[
                    "severe_sla_violation_rate"
                ],
                "avg_latency_excess_ms": latency_summary[
                    "avg_latency_excess_ms"
                ],
                "max_latency_excess_ms": latency_summary[
                    "max_latency_excess_ms"
                ],
                "avg_resource_utilization": strategy_frame[
                    "resource_utilization"
                ].mean(),
                "avg_effective_throughput": strategy_frame[
                    "effective_throughput"
                ].mean(),
                "resource_fairness_jain": strategy_frame[
                    "resource_fairness_jain"
                ].mean(),
                "throughput_fairness_jain": strategy_frame[
                    "throughput_fairness_jain"
                ].mean(),
                "avg_prediction_error_abs": strategy_frame[
                    "prediction_error_abs"
                ].mean(),
                "prediction_mae": prediction_summary["prediction_mae"],
                "prediction_rmse": prediction_summary["prediction_rmse"],
                "prediction_mape": prediction_summary["prediction_mape"],
                "avg_incentive_score": strategy_frame[
                    "incentive_score"
                ].mean(),
                "centralized_overhead_bytes": overhead_summary[
                    "centralized_overhead_bytes"
                ],
                "federated_overhead_bytes": overhead_summary[
                    "federated_overhead_bytes"
                ],
                "communication_overhead_bytes": overhead_summary[
                    "communication_overhead_bytes"
                ],
                "overhead_reduction_ratio": overhead_summary[
                    "overhead_reduction_ratio"
                ],
                "network_utility_score": utility_score,
            }
        )

    summary_metrics = pd.DataFrame(summary_rows)
    numeric_columns = summary_metrics.select_dtypes(include=["number"]).columns
    summary_metrics[numeric_columns] = summary_metrics[numeric_columns].round(4)

    return summary_metrics


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

    if "predicted_demand" not in merged.columns:
        merged["predicted_demand"] = np.nan

    capacity = merged["allocated_resource_units"].replace(0, _EPSILON)
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

    sla_threshold = config.network.sla_latency_threshold_ms
    severe_sla_threshold = 2.0 * sla_threshold

    merged["sla_violation"] = (merged["latency_ms"] > sla_threshold).astype(int)

    merged["severe_sla_violation"] = (
        merged["latency_ms"] > severe_sla_threshold
    ).astype(int)

    merged["latency_excess_ms"] = (
        merged["latency_ms"] - sla_threshold
    ).clip(lower=0.0).round(4)

    merged["effective_throughput"] = (
        merged["allocated_resource_units"]
        * (1.0 - 0.35 * merged["quality_risk"])
        * (1.0 - 0.50 * overload_ratio.clip(upper=1.0))
    ).clip(lower=0.0).round(4)

    fairness_groups = merged.groupby(["time_step", "strategy"], sort=False)

    merged["resource_fairness_jain"] = fairness_groups[
        "allocated_resource_units"
    ].transform(lambda values: jain_fairness_index(values.to_list()))

    merged["throughput_fairness_jain"] = fairness_groups[
        "effective_throughput"
    ].transform(lambda values: jain_fairness_index(values.to_list()))

    merged["resource_fairness_jain"] = merged["resource_fairness_jain"].round(4)
    merged["throughput_fairness_jain"] = merged[
        "throughput_fairness_jain"
    ].round(4)

    per_step_metrics = merged[
        [
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
        ]
    ].copy()

    summary_metrics = _build_summary_metrics(
        per_step_metrics=per_step_metrics,
        config=config,
    )

    return per_step_metrics, summary_metrics
