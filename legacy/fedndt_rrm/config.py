from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    random_seed: int = 42
    time_steps: int = Field(default=100, gt=0)


class NetworkConfig(BaseModel):
    num_edge_nodes: int = Field(default=3, gt=0)
    num_users: int = Field(default=60, gt=0)
    total_resource_units: float = Field(default=120.0, gt=0)
    base_latency_ms: float = Field(default=10.0, gt=0)
    sla_latency_threshold_ms: float = Field(default=50.0, gt=0)


class TrafficConfig(BaseModel):
    profile: str = "peak"
    base_demand: float = Field(default=1.0, gt=0)
    peak_multiplier: float = Field(default=2.5, gt=0)
    noise_std: float = Field(default=0.25, ge=0)


class RadioConfig(BaseModel):
    base_quality: float = 20.0
    distance_loss_factor: float = Field(default=0.08, ge=0)
    interference_mean: float = Field(default=2.0, ge=0)
    interference_std: float = Field(default=0.7, ge=0)
    quality_noise_std: float = Field(default=1.0, ge=0)


class FederatedConfig(BaseModel):
    rounds_per_step: int = Field(default=1, gt=0)
    history_window: int = Field(default=8, gt=1)
    prediction_smoothing: float = Field(default=0.65, ge=0, le=1)


class IncentiveConfig(BaseModel):
    enabled: bool = True
    freshness_weight: float = 0.25
    accuracy_weight: float = 0.35
    consistency_weight: float = 0.30
    fairness_weight: float = 0.10


class StressConfig(BaseModel):
    enabled: bool = False

    # Creates an overloaded Edge/RAN domain during a selected time window.
    overloaded_edge_node_id: int = Field(default=1, ge=0)
    overload_start_step: int = Field(default=45, ge=0)
    overload_end_step: int = Field(default=75, ge=0)
    overload_multiplier: float = Field(default=2.4, gt=1.0)
    mobility_shift_probability: float = Field(default=0.20, ge=0.0, le=1.0)

    # Creates stale/noisy reporting from one Edge/RAN domain.
    unreliable_edge_node_id: int = Field(default=2, ge=0)
    stale_update_probability: float = Field(default=0.25, ge=0.0, le=1.0)
    report_noise_probability: float = Field(default=0.30, ge=0.0, le=1.0)
    report_noise_std: float = Field(default=0.45, ge=0.0)

    # Makes the centralized greedy baseline more realistic.
    greedy_observation_delay_steps: int = Field(default=4, ge=0)


class NetworkModelConfig(BaseModel):
    """Calibration parameters for network-level radio/queueing abstractions."""

    bandwidth_mhz_per_resource_unit: float = Field(default=0.25, gt=0)
    reference_sinr_db: float = 10.0
    min_service_factor: float = Field(default=0.30, gt=0)
    max_service_factor: float = Field(default=2.20, gt=0)
    service_rate_calibration_multiplier: float = Field(default=1.90, gt=0)
    queue_delay_scale_ms: float = Field(default=120.0, gt=0)
    max_queue_delay_ms: float = Field(default=900.0, gt=0)
    radio_delay_scale_ms: float = Field(default=4.0, gt=0)
    max_radio_delay_ms: float = Field(default=250.0, gt=0)
    base_backhaul_delay_ms: float = Field(default=3.0, ge=0)
    max_total_latency_ms: float = Field(default=10000.0, gt=0)


class ExperimentConfig(BaseModel):
    simulation: SimulationConfig
    network: NetworkConfig
    traffic: TrafficConfig
    radio: RadioConfig
    federated: FederatedConfig
    incentive: IncentiveConfig
    stress: StressConfig = Field(default_factory=StressConfig)
    network_model: NetworkModelConfig = Field(default_factory=NetworkModelConfig)


def load_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file)

    return ExperimentConfig.model_validate(raw)
