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
    total_resource_units: float = Field(default=300.0, gt=0)
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


class ExperimentConfig(BaseModel):
    simulation: SimulationConfig
    network: NetworkConfig
    traffic: TrafficConfig
    radio: RadioConfig
    federated: FederatedConfig
    incentive: IncentiveConfig


def load_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file)

    return ExperimentConfig.model_validate(raw)
