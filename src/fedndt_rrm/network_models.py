from __future__ import annotations

import math


_EPSILON = 1e-9


def db_to_linear(value_db: float) -> float:
    """Convert dB value to linear scale."""
    return 10.0 ** (float(value_db) / 10.0)


def linear_to_db(value_linear: float) -> float:
    """Convert linear value to dB scale."""
    value = max(float(value_linear), _EPSILON)
    return 10.0 * math.log10(value)


def log_distance_path_loss_db(
    *,
    distance_m: float,
    reference_distance_m: float = 1.0,
    reference_path_loss_db: float = 30.0,
    path_loss_exponent: float = 3.0,
) -> float:
    """Compute simplified log-distance path loss.

    Formula:
        PL(d) = PL_0 + 10 n log10(d / d_0)

    This is a network-level abstraction, not a calibrated RF propagation model.
    """
    distance = max(float(distance_m), _EPSILON)
    reference_distance = max(float(reference_distance_m), _EPSILON)

    if path_loss_exponent < 0:
        msg = "path_loss_exponent must be non-negative"
        raise ValueError(msg)

    return float(reference_path_loss_db) + (
        10.0 * float(path_loss_exponent) * math.log10(distance / reference_distance)
    )


def received_power_dbm(
    *,
    transmit_power_dbm: float,
    path_loss_db: float,
) -> float:
    """Compute received-power abstraction in dBm."""
    return float(transmit_power_dbm) - float(path_loss_db)


def sinr_linear_from_dbm(
    *,
    received_power_dbm_value: float,
    interference_power_dbm: float,
    noise_power_dbm: float,
) -> float:
    """Compute SINR in linear scale from dBm powers.

    Formula:
        SINR = P_rx / (I + N)
    """
    received_power_linear = db_to_linear(received_power_dbm_value)
    interference_linear = db_to_linear(interference_power_dbm)
    noise_linear = db_to_linear(noise_power_dbm)

    denominator = max(interference_linear + noise_linear, _EPSILON)
    return received_power_linear / denominator


def shannon_capacity_mbps(
    *,
    bandwidth_mhz: float,
    sinr_linear: float,
) -> float:
    """Compute Shannon-Hartley-inspired capacity in Mbps.

    Formula:
        C = B log2(1 + SINR)

    If B is given in MHz, the output is in Mbit/s because:
        MHz * bits/s/Hz = Mbit/s
    """
    bandwidth = max(float(bandwidth_mhz), 0.0)
    sinr = max(float(sinr_linear), 0.0)

    return bandwidth * math.log2(1.0 + sinr)


def queue_utilization(
    *,
    arrival_rate: float,
    service_rate: float,
) -> float:
    """Compute queue/load utilization.

    Formula:
        rho = lambda / mu
    """
    service = max(float(service_rate), _EPSILON)
    arrival = max(float(arrival_rate), 0.0)
    return arrival / service


def queue_delay_ms(
    *,
    arrival_rate: float,
    service_rate: float,
    base_scale_ms: float = 1000.0,
    epsilon: float = 1e-6,
    max_delay_ms: float = 5000.0,
) -> float:
    """Compute queueing-inspired delay.

    Stable approximation:
        D_queue = base_scale / max(mu - lambda, epsilon)

    The output is capped to keep the simulator stable and explainable.
    """
    arrival = max(float(arrival_rate), 0.0)
    service = max(float(service_rate), 0.0)
    remaining_capacity = max(service - arrival, float(epsilon))

    delay = float(base_scale_ms) / remaining_capacity
    return min(delay, float(max_delay_ms))


def bounded_total_latency_ms(
    *,
    base_latency_ms: float,
    radio_delay_ms: float,
    queue_delay_ms_value: float,
    backhaul_delay_ms: float = 0.0,
    max_latency_ms: float = 10000.0,
) -> float:
    """Compose bounded total network-level latency.

    Formula:
        D = D_base + D_radio + D_queue + D_backhaul
    """
    total_latency = (
        max(float(base_latency_ms), 0.0)
        + max(float(radio_delay_ms), 0.0)
        + max(float(queue_delay_ms_value), 0.0)
        + max(float(backhaul_delay_ms), 0.0)
    )

    return min(total_latency, float(max_latency_ms))


def radio_delay_from_capacity_ms(
    *,
    demand_units: float,
    capacity_units: float,
    scale_ms: float = 10.0,
    max_delay_ms: float = 1000.0,
) -> float:
    """Estimate radio delay from demand-to-capacity pressure.

    This is a lightweight abstraction:
        higher demand/capacity pressure -> higher radio delay.
    """
    demand = max(float(demand_units), 0.0)
    capacity = max(float(capacity_units), _EPSILON)

    delay = float(scale_ms) * (demand / capacity)
    return min(delay, float(max_delay_ms))
