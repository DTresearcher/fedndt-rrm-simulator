from __future__ import annotations

import math
from collections.abc import Sequence


_EPSILON = 1e-9


def _clean_numeric_values(values: Sequence[float]) -> list[float]:
    """Return finite numeric values only.

    Scientific metric functions should be stable when a simulation produces
    empty, missing, or non-finite intermediate values.
    """
    cleaned: list[float] = []
    for value in values:
        numeric_value = float(value)
        if math.isfinite(numeric_value):
            cleaned.append(numeric_value)
    return cleaned


def safe_mean(values: Sequence[float], default: float = 0.0) -> float:
    """Compute a stable arithmetic mean."""
    cleaned = _clean_numeric_values(values)
    if not cleaned:
        return default
    return sum(cleaned) / len(cleaned)


def percentile(values: Sequence[float], percentile_value: float) -> float:
    """Compute a deterministic percentile using linear interpolation.

    Args:
        values: Numeric values.
        percentile_value: Percentile in [0, 100].

    Returns:
        Interpolated percentile value. Returns 0.0 for an empty input.
    """
    if percentile_value < 0 or percentile_value > 100:
        msg = "percentile_value must be in the range [0, 100]"
        raise ValueError(msg)

    cleaned = sorted(_clean_numeric_values(values))
    if not cleaned:
        return 0.0

    if len(cleaned) == 1:
        return cleaned[0]

    rank = (len(cleaned) - 1) * (percentile_value / 100.0)
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)

    if lower_index == upper_index:
        return cleaned[int(rank)]

    lower_value = cleaned[lower_index]
    upper_value = cleaned[upper_index]
    interpolation_weight = rank - lower_index
    return lower_value + (upper_value - lower_value) * interpolation_weight


def jain_fairness_index(values: Sequence[float]) -> float:
    """Compute Jain's fairness index.

    Formula:
        J(x) = (sum_i x_i)^2 / (n * sum_i x_i^2)

    Range:
        0 < J(x) <= 1 for positive allocations.
        1 means perfectly fair/equal allocation.

    Returns 0.0 when the vector is empty or has no positive mass.
    """
    cleaned = [max(0.0, value) for value in _clean_numeric_values(values)]
    if not cleaned:
        return 0.0

    numerator = sum(cleaned) ** 2
    denominator = len(cleaned) * sum(value**2 for value in cleaned)

    if denominator <= _EPSILON:
        return 0.0

    return numerator / denominator


def latency_severity_summary(
    latencies_ms: Sequence[float],
    sla_threshold_ms: float,
    severe_multiplier: float = 2.0,
) -> dict[str, float]:
    """Summarize latency and SLA-severity behavior.

    A normal SLA violation occurs when latency > SLA threshold.
    A severe SLA violation occurs when latency > severe_multiplier * SLA threshold.

    This separates raw violation frequency from violation magnitude, which is
    important when a strategy has fewer violations but much worse tail latency.
    """
    cleaned = _clean_numeric_values(latencies_ms)
    if not cleaned:
        return {
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "sla_violation_rate": 0.0,
            "severe_sla_violation_rate": 0.0,
            "avg_latency_excess_ms": 0.0,
            "max_latency_excess_ms": 0.0,
        }

    threshold = float(sla_threshold_ms)
    severe_threshold = threshold * float(severe_multiplier)
    excess_values = [max(0.0, latency - threshold) for latency in cleaned]

    violation_count = sum(latency > threshold for latency in cleaned)
    severe_violation_count = sum(latency > severe_threshold for latency in cleaned)

    return {
        "avg_latency_ms": safe_mean(cleaned),
        "p95_latency_ms": percentile(cleaned, 95),
        "p99_latency_ms": percentile(cleaned, 99),
        "sla_violation_rate": violation_count / len(cleaned),
        "severe_sla_violation_rate": severe_violation_count / len(cleaned),
        "avg_latency_excess_ms": safe_mean(excess_values),
        "max_latency_excess_ms": max(excess_values),
    }


def prediction_error_summary(
    actual_values: Sequence[float],
    predicted_values: Sequence[float],
) -> dict[str, float]:
    """Compute deterministic prediction error metrics.

    Metrics:
        MAE  = mean absolute error
        RMSE = root mean squared error
        MAPE = mean absolute percentage error, stabilized with epsilon
    """
    paired_values = [
        (float(actual), float(predicted))
        for actual, predicted in zip(actual_values, predicted_values, strict=False)
        if math.isfinite(float(actual)) and math.isfinite(float(predicted))
    ]

    if not paired_values:
        return {
            "prediction_mae": 0.0,
            "prediction_rmse": 0.0,
            "prediction_mape": 0.0,
        }

    absolute_errors = [abs(actual - predicted) for actual, predicted in paired_values]
    squared_errors = [
        (actual - predicted) ** 2 for actual, predicted in paired_values
    ]
    percentage_errors = [
        abs(actual - predicted) / max(abs(actual), _EPSILON)
        for actual, predicted in paired_values
    ]

    return {
        "prediction_mae": safe_mean(absolute_errors),
        "prediction_rmse": math.sqrt(safe_mean(squared_errors)),
        "prediction_mape": safe_mean(percentage_errors),
    }


def communication_overhead_proxy(
    *,
    num_nodes: int,
    centralized_state_size_bytes: float,
    centralized_frequency_hz: float,
    participating_nodes: int,
    federated_model_update_size_bytes: float,
    federated_rounds: int,
) -> dict[str, float]:
    """Estimate centralized vs federated communication overhead.

    Centralized proxy:
        O_c = number_of_nodes * state_size * frequency

    Federated proxy:
        O_f = participating_nodes * model_update_size * rounds

    The function returns a proxy rather than a measured network trace.
    It is suitable for relative comparison in a network-level simulator.
    """
    centralized_bytes = (
        max(0, int(num_nodes))
        * max(0.0, float(centralized_state_size_bytes))
        * max(0.0, float(centralized_frequency_hz))
    )

    federated_bytes = (
        max(0, int(participating_nodes))
        * max(0.0, float(federated_model_update_size_bytes))
        * max(0, int(federated_rounds))
    )

    overhead_reduction_ratio = 0.0
    if centralized_bytes > _EPSILON:
        overhead_reduction_ratio = (centralized_bytes - federated_bytes) / centralized_bytes

    return {
        "centralized_overhead_bytes": centralized_bytes,
        "federated_overhead_bytes": federated_bytes,
        "overhead_reduction_ratio": overhead_reduction_ratio,
    }


def alpha_fair_utility(value: float, alpha: float = 1.0) -> float:
    """Compute alpha-fair utility for a single positive value.

    Formula:
        U_alpha(x) = log(x), if alpha = 1
        U_alpha(x) = x^(1-alpha) / (1-alpha), otherwise

    x is stabilized using epsilon to avoid log(0).
    """
    x_value = max(float(value), _EPSILON)
    alpha_value = float(alpha)

    if math.isclose(alpha_value, 1.0):
        return math.log(x_value)

    return (x_value ** (1.0 - alpha_value)) / (1.0 - alpha_value)


def aggregate_alpha_fair_utility(
    values: Sequence[float],
    alpha: float = 1.0,
) -> float:
    """Aggregate alpha-fair utility across nodes/users."""
    cleaned = _clean_numeric_values(values)
    if not cleaned:
        return 0.0
    return sum(alpha_fair_utility(value, alpha=alpha) for value in cleaned)


def network_utility_score(
    *,
    throughputs: Sequence[float],
    mean_latency_excess_ms: float,
    sla_violation_rate: float,
    communication_overhead_bytes: float,
    latency_penalty_weight: float = 1.0,
    sla_penalty_weight: float = 1.0,
    overhead_penalty_weight: float = 1e-6,
) -> float:
    """Compute a utility-style network objective.

    Proposed objective:
        U(t) = sum_j log(throughput_j + epsilon)
               - lambda_1 * mean_latency_excess
               - lambda_2 * SLA_violation_rate
               - lambda_3 * communication_overhead

    This is not claimed as a globally optimal network-control solution.
    It is a transparent framework-level utility score for comparing policies.
    """
    throughput_utility = aggregate_alpha_fair_utility(throughputs, alpha=1.0)

    return (
        throughput_utility
        - float(latency_penalty_weight) * max(0.0, float(mean_latency_excess_ms))
        - float(sla_penalty_weight) * max(0.0, float(sla_violation_rate))
        - float(overhead_penalty_weight)
        * max(0.0, float(communication_overhead_bytes))
    )
