from __future__ import annotations

import math

import pytest

from fedndt_rrm.network_models import (
    bounded_total_latency_ms,
    db_to_linear,
    linear_to_db,
    log_distance_path_loss_db,
    queue_delay_ms,
    queue_utilization,
    radio_delay_from_capacity_ms,
    received_power_dbm,
    shannon_capacity_mbps,
    sinr_linear_from_dbm,
)


def test_db_linear_roundtrip() -> None:
    value_db = 10.0
    value_linear = db_to_linear(value_db)

    assert value_linear == pytest.approx(10.0)
    assert linear_to_db(value_linear) == pytest.approx(value_db)


def test_log_distance_path_loss_increases_with_distance() -> None:
    near_loss = log_distance_path_loss_db(distance_m=10.0)
    far_loss = log_distance_path_loss_db(distance_m=100.0)

    assert far_loss > near_loss


def test_received_power_decreases_with_path_loss() -> None:
    received = received_power_dbm(
        transmit_power_dbm=30.0,
        path_loss_db=80.0,
    )

    assert received == pytest.approx(-50.0)


def test_sinr_linear_from_dbm_is_positive() -> None:
    sinr = sinr_linear_from_dbm(
        received_power_dbm_value=-60.0,
        interference_power_dbm=-80.0,
        noise_power_dbm=-90.0,
    )

    assert sinr > 0


def test_shannon_capacity_increases_with_sinr() -> None:
    low_capacity = shannon_capacity_mbps(
        bandwidth_mhz=10.0,
        sinr_linear=1.0,
    )
    high_capacity = shannon_capacity_mbps(
        bandwidth_mhz=10.0,
        sinr_linear=10.0,
    )

    assert high_capacity > low_capacity


def test_queue_utilization() -> None:
    rho = queue_utilization(arrival_rate=50.0, service_rate=100.0)

    assert rho == pytest.approx(0.5)


def test_queue_delay_grows_as_capacity_margin_shrinks() -> None:
    low_delay = queue_delay_ms(
        arrival_rate=20.0,
        service_rate=100.0,
        base_scale_ms=100.0,
    )
    high_delay = queue_delay_ms(
        arrival_rate=95.0,
        service_rate=100.0,
        base_scale_ms=100.0,
    )

    assert high_delay > low_delay


def test_queue_delay_is_capped() -> None:
    delay = queue_delay_ms(
        arrival_rate=100.0,
        service_rate=100.0,
        max_delay_ms=123.0,
    )

    assert delay == pytest.approx(123.0)


def test_bounded_total_latency_ms() -> None:
    latency = bounded_total_latency_ms(
        base_latency_ms=10.0,
        radio_delay_ms=5.0,
        queue_delay_ms_value=20.0,
        backhaul_delay_ms=3.0,
    )

    assert latency == pytest.approx(38.0)


def test_radio_delay_from_capacity_ms() -> None:
    low_pressure = radio_delay_from_capacity_ms(
        demand_units=10.0,
        capacity_units=100.0,
    )
    high_pressure = radio_delay_from_capacity_ms(
        demand_units=80.0,
        capacity_units=100.0,
    )

    assert high_pressure > low_pressure


def test_shannon_capacity_zero_bandwidth() -> None:
    capacity = shannon_capacity_mbps(
        bandwidth_mhz=0.0,
        sinr_linear=10.0,
    )

    assert capacity == pytest.approx(0.0)


def test_log_distance_path_loss_rejects_negative_exponent() -> None:
    with pytest.raises(ValueError):
        log_distance_path_loss_db(
            distance_m=10.0,
            path_loss_exponent=-1.0,
        )


def test_capacity_matches_known_log_case() -> None:
    capacity = shannon_capacity_mbps(
        bandwidth_mhz=20.0,
        sinr_linear=3.0,
    )

    assert capacity == pytest.approx(40.0)


def test_linear_to_db_handles_zero_safely() -> None:
    value = linear_to_db(0.0)

    assert math.isfinite(value)
