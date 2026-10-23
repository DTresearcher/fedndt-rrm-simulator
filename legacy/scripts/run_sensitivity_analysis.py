from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

import pandas as pd

from fedndt_rrm.config import ExperimentConfig, load_config
from fedndt_rrm.digital_twin import add_demand_predictions, build_local_digital_twins
from fedndt_rrm.incentive_engine import add_incentive_scores
from fedndt_rrm.metrics import evaluate_allocations
from fedndt_rrm.resource_allocator import allocate_resources
from fedndt_rrm.scenario import generate_synthetic_telemetry
from fedndt_rrm.scenario_analysis import (
    build_key_claim_summary,
    compute_strategy_improvements,
)


DEFAULT_SCENARIOS = [
    "configs/stress_unreliable_nodes.yaml",
    "configs/mobility_stress.yaml",
    "configs/overload_stress.yaml",
    "configs/high_noise_radio_stress.yaml",
    "configs/low_capacity_edge_stress.yaml",
]


SENSITIVITY_VARIANTS: dict[str, dict[str, float]] = {
    "baseline_calibrated": {},
    "lighter_queue_penalty": {
        "queue_delay_scale_ms": 80.0,
        "service_rate_calibration_multiplier": 2.20,
    },
    "heavier_queue_penalty": {
        "queue_delay_scale_ms": 160.0,
        "service_rate_calibration_multiplier": 1.60,
    },
    "lower_radio_penalty": {
        "radio_delay_scale_ms": 2.5,
        "max_radio_delay_ms": 180.0,
    },
    "higher_radio_penalty": {
        "radio_delay_scale_ms": 6.0,
        "max_radio_delay_ms": 350.0,
    },
}


def _apply_variant(
    config: ExperimentConfig,
    overrides: dict[str, float],
) -> ExperimentConfig:
    config_copy = deepcopy(config)

    for field_name, value in overrides.items():
        setattr(config_copy.network_model, field_name, value)

    return config_copy


def _run_config(config: ExperimentConfig) -> pd.DataFrame:
    telemetry, _ = generate_synthetic_telemetry(config)
    ndt_state = build_local_digital_twins(telemetry, config)
    ndt_state = add_demand_predictions(ndt_state, config)
    ndt_state = add_incentive_scores(ndt_state, config)

    allocations = allocate_resources(ndt_state, config)
    _, summary_metrics = evaluate_allocations(
        ndt_state=ndt_state,
        allocations=allocations,
        config=config,
    )

    return summary_metrics


def _variant_metadata(config: ExperimentConfig) -> dict[str, float]:
    return {
        "bandwidth_mhz_per_resource_unit": (
            config.network_model.bandwidth_mhz_per_resource_unit
        ),
        "service_rate_calibration_multiplier": (
            config.network_model.service_rate_calibration_multiplier
        ),
        "queue_delay_scale_ms": config.network_model.queue_delay_scale_ms,
        "max_queue_delay_ms": config.network_model.max_queue_delay_ms,
        "radio_delay_scale_ms": config.network_model.radio_delay_scale_ms,
        "max_radio_delay_ms": config.network_model.max_radio_delay_ms,
        "base_backhaul_delay_ms": config.network_model.base_backhaul_delay_ms,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run calibration sensitivity analysis for FedNDT-RRM."
    )
    parser.add_argument(
        "--config",
        action="append",
        dest="configs",
        help=(
            "Scenario config path. Can be provided multiple times. "
            "Defaults to selected stress scenarios."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="results/sensitivity_analysis",
        help="Directory where sensitivity outputs will be saved.",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_paths = [Path(path) for path in (args.configs or DEFAULT_SCENARIOS)]

    comparison_frames: list[pd.DataFrame] = []
    claim_frames: list[pd.DataFrame] = []

    for config_path in config_paths:
        base_config = load_config(config_path)
        scenario_name = config_path.stem

        for variant_name, overrides in SENSITIVITY_VARIANTS.items():
            config = _apply_variant(base_config, overrides)
            summary_metrics = _run_config(config)

            comparison = summary_metrics.copy()
            comparison.insert(0, "scenario", scenario_name)
            comparison.insert(1, "sensitivity_variant", variant_name)
            comparison.insert(2, "config_path", str(config_path))

            for key, value in _variant_metadata(config).items():
                comparison[key] = value

            comparison_frames.append(comparison)

            improvements_input = comparison.drop(
                columns=[
                    "sensitivity_variant",
                    "config_path",
                    "bandwidth_mhz_per_resource_unit",
                    "service_rate_calibration_multiplier",
                    "queue_delay_scale_ms",
                    "max_queue_delay_ms",
                    "radio_delay_scale_ms",
                    "max_radio_delay_ms",
                    "base_backhaul_delay_ms",
                ],
                errors="ignore",
            )

            improvements = compute_strategy_improvements(improvements_input)
            claims = build_key_claim_summary(improvements)
            claims.insert(0, "sensitivity_variant", variant_name)
            claims.insert(1, "config_path", str(config_path))

            for key, value in _variant_metadata(config).items():
                claims[key] = value

            claim_frames.append(claims)

            print(f"Completed {scenario_name} / {variant_name}")

    comparison_output = pd.concat(comparison_frames, ignore_index=True)
    claims_output = pd.concat(claim_frames, ignore_index=True)

    comparison_output.to_csv(
        output_dir / "sensitivity_comparison.csv",
        index=False,
    )
    claims_output.to_csv(
        output_dir / "sensitivity_claim_summary.csv",
        index=False,
    )

    robustness = (
        claims_output.groupby(
            [
                "baseline_strategy",
                "metric",
                "claim_strength",
            ]
        )
        .size()
        .reset_index(name="count")
        .sort_values(["baseline_strategy", "metric", "claim_strength"])
    )

    robustness.to_csv(
        output_dir / "claim_strength_counts.csv",
        index=False,
    )

    print()
    print("Sensitivity analysis completed successfully")
    print(f"Output directory: {output_dir}")
    print()
    print("Claim-strength counts:")
    print(robustness.to_string(index=False))


if __name__ == "__main__":
    main()
