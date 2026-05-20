from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from fedndt_rrm.config import ExperimentConfig


@dataclass(frozen=True)
class TelemetrySummary:
    total_records: int
    time_steps: int
    num_users: int
    num_edge_nodes: int
    avg_user_demand: float
    avg_radio_quality: float
    avg_throughput_potential: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "time_steps": self.time_steps,
            "num_users": self.num_users,
            "num_edge_nodes": self.num_edge_nodes,
            "avg_user_demand": round(self.avg_user_demand, 4),
            "avg_radio_quality": round(self.avg_radio_quality, 4),
            "avg_throughput_potential": round(self.avg_throughput_potential, 4),
        }


def _peak_multiplier(time_step: int, total_steps: int, peak_multiplier: float) -> float:
    """
    Creates a smooth peak-traffic curve.

    The demand increases around the middle-late part of the simulation,
    representing an evening/business-hour congestion period.
    """
    if total_steps <= 1:
        return 1.0

    normalized_time = time_step / (total_steps - 1)
    peak_center = 0.65
    peak_width = 0.16

    gaussian_peak = np.exp(-((normalized_time - peak_center) ** 2) / (2 * peak_width**2))
    return 1.0 + (peak_multiplier - 1.0) * gaussian_peak


def _calculate_radio_quality(
    base_quality: float,
    distance: float,
    distance_loss_factor: float,
    interference: float,
    noise: float,
) -> float:
    """
    Abstract network-level radio-quality model.

    This is not physical-layer waveform simulation. It represents radio quality
    using distance loss, interference, and random noise, producing a SINR-like
    quality indicator suitable for resource-management simulation.
    """
    quality = base_quality - (distance_loss_factor * distance) - interference + noise
    return float(max(0.1, quality))


def _calculate_throughput_potential(radio_quality: float) -> float:
    """
    Converts the abstract radio-quality indicator into a throughput potential.

    The log2(1 + quality) form follows the intuition of capacity increasing
    sub-linearly as signal quality improves.
    """
    return float(10.0 * np.log2(1.0 + radio_quality))


def generate_synthetic_telemetry(config: ExperimentConfig) -> tuple[pd.DataFrame, TelemetrySummary]:
    rng = np.random.default_rng(config.simulation.random_seed)

    time_steps = config.simulation.time_steps
    num_users = config.network.num_users
    num_edge_nodes = config.network.num_edge_nodes

    # Each user is initially associated with one Edge/RAN domain.
    user_home_nodes = rng.integers(low=0, high=num_edge_nodes, size=num_users)

    # Approximate user distance from serving cell/edge domain in meters.
    # Kept at network-abstraction level, not physical RF simulation.
    user_base_distances = rng.uniform(low=20.0, high=150.0, size=num_users)

    records: list[dict[str, Any]] = []

    for time_step in range(time_steps):
        demand_multiplier = _peak_multiplier(
            time_step=time_step,
            total_steps=time_steps,
            peak_multiplier=config.traffic.peak_multiplier,
        )

        # Slightly higher mobility/handover probability during peak periods.
        handover_probability = min(0.12, 0.03 + 0.03 * demand_multiplier)

        for user_id in range(num_users):
            if rng.random() < handover_probability:
                edge_node_id = int(rng.integers(low=0, high=num_edge_nodes))
            else:
                edge_node_id = int(user_home_nodes[user_id])

            mobility_noise = rng.normal(loc=0.0, scale=8.0 + 3.0 * demand_multiplier)
            distance = float(np.clip(user_base_distances[user_id] + mobility_noise, 5.0, 250.0))

            user_variation = rng.lognormal(mean=0.0, sigma=0.35)
            demand_noise = rng.normal(loc=0.0, scale=config.traffic.noise_std)

            traffic_demand = config.traffic.base_demand * demand_multiplier * user_variation
            traffic_demand = float(max(0.05, traffic_demand + demand_noise))

            interference = float(
                max(
                    0.0,
                    rng.normal(
                        loc=config.radio.interference_mean,
                        scale=config.radio.interference_std,
                    ),
                )
            )

            quality_noise = float(rng.normal(loc=0.0, scale=config.radio.quality_noise_std))

            radio_quality = _calculate_radio_quality(
                base_quality=config.radio.base_quality,
                distance=distance,
                distance_loss_factor=config.radio.distance_loss_factor,
                interference=interference,
                noise=quality_noise,
            )

            throughput_potential = _calculate_throughput_potential(radio_quality)

            records.append(
                {
                    "time_step": time_step,
                    "user_id": user_id,
                    "edge_node_id": edge_node_id,
                    "distance_m": round(distance, 4),
                    "traffic_demand": round(traffic_demand, 4),
                    "interference": round(interference, 4),
                    "radio_quality": round(radio_quality, 4),
                    "throughput_potential": round(throughput_potential, 4),
                }
            )

    telemetry = pd.DataFrame.from_records(records)

    summary = TelemetrySummary(
        total_records=len(telemetry),
        time_steps=time_steps,
        num_users=num_users,
        num_edge_nodes=num_edge_nodes,
        avg_user_demand=float(telemetry["traffic_demand"].mean()),
        avg_radio_quality=float(telemetry["radio_quality"].mean()),
        avg_throughput_potential=float(telemetry["throughput_potential"].mean()),
    )

    return telemetry, summary
