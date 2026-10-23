from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from fedndt_rrm.config import load_config
from fedndt_rrm.digital_twin import add_demand_predictions, build_local_digital_twins
from fedndt_rrm.incentive_engine import add_incentive_scores
from fedndt_rrm.metrics import evaluate_allocations
from fedndt_rrm.resource_allocator import allocate_resources
from fedndt_rrm.scenario import generate_synthetic_telemetry


DEFAULT_SCENARIO_CONFIGS = [
    "configs/peak_traffic.yaml",
    "configs/stress_unreliable_nodes.yaml",
    "configs/stress_unreliable_no_incentive.yaml",
    "configs/stress_without_greedy_delay.yaml",
    "configs/mobility_stress.yaml",
    "configs/overload_stress.yaml",
    "configs/high_noise_radio_stress.yaml",
    "configs/low_capacity_edge_stress.yaml",
]


LATEX_READY_COLUMNS = [
    "scenario",
    "strategy",
    "avg_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "sla_violation_rate",
    "severe_sla_violation_rate",
    "avg_latency_excess_ms",
    "max_latency_excess_ms",
    "resource_fairness_jain",
    "throughput_fairness_jain",
    "overhead_reduction_ratio",
    "network_utility_score",
]


def _scenario_name_from_config(config_path: Path) -> str:
    return config_path.stem


def _run_single_scenario(
    *,
    config_path: Path,
    scenario_output_dir: Path,
) -> pd.DataFrame:
    scenario_name = _scenario_name_from_config(config_path)
    config = load_config(config_path)

    scenario_output_dir.mkdir(parents=True, exist_ok=True)

    telemetry, telemetry_summary = generate_synthetic_telemetry(config)
    ndt_state = build_local_digital_twins(telemetry, config)
    ndt_state = add_demand_predictions(ndt_state, config)
    ndt_state = add_incentive_scores(ndt_state, config)

    allocations = allocate_resources(ndt_state, config)
    per_step_metrics, summary_metrics = evaluate_allocations(
        ndt_state=ndt_state,
        allocations=allocations,
        config=config,
    )

    telemetry.to_csv(scenario_output_dir / "raw_telemetry.csv", index=False)
    ndt_state.to_csv(scenario_output_dir / "ndt_state.csv", index=False)
    allocations.to_csv(scenario_output_dir / "allocations.csv", index=False)
    per_step_metrics.to_csv(scenario_output_dir / "metrics.csv", index=False)
    summary_metrics.to_csv(
        scenario_output_dir / "summary_metrics.csv",
        index=False,
    )

    summary = {
        "scenario": scenario_name,
        "config_path": str(config_path),
        "telemetry": telemetry_summary.to_dict(),
        "simulation": {
            "random_seed": config.simulation.random_seed,
            "time_steps": config.simulation.time_steps,
            "num_edge_nodes": config.network.num_edge_nodes,
            "num_users": config.network.num_users,
            "total_resource_units": config.network.total_resource_units,
            "sla_latency_threshold_ms": config.network.sla_latency_threshold_ms,
            "incentive_enabled": config.incentive.enabled,
            "stress_enabled": config.stress.enabled,
        },
        "summary_metrics": summary_metrics.to_dict(orient="records"),
    }

    with (scenario_output_dir / "summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    comparison_rows = summary_metrics.copy()
    comparison_rows.insert(0, "scenario", scenario_name)
    comparison_rows.insert(1, "config_path", str(config_path))

    return comparison_rows


def _write_comparison_outputs(
    *,
    comparison: pd.DataFrame,
    output_dir: Path,
) -> None:
    comparison.to_csv(output_dir / "scenario_comparison.csv", index=False)

    available_latex_columns = [
        column for column in LATEX_READY_COLUMNS if column in comparison.columns
    ]
    latex_ready = comparison[available_latex_columns].copy()

    latex_ready.to_csv(
        output_dir / "scenario_comparison_latex_ready.csv",
        index=False,
    )

    latex_table = latex_ready.to_latex(
        index=False,
        float_format="%.4f",
        caption=(
            "Scenario-level comparison of resource-allocation strategies "
            "under network-level FedNDT-RRM simulation."
        ),
        label="tab:scenario-comparison",
    )

    with (output_dir / "scenario_comparison_latex.tex").open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(latex_table)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the FedNDT-RRM scenario suite.",
    )
    parser.add_argument(
        "--config",
        action="append",
        dest="configs",
        help=(
            "Scenario config path. Can be provided multiple times. "
            "Defaults to the built-in scenario suite."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="results/scenario_suite",
        help="Directory where scenario-suite outputs will be saved.",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_paths = [
        Path(config_path)
        for config_path in (args.configs if args.configs else DEFAULT_SCENARIO_CONFIGS)
    ]

    missing_configs = [
        str(config_path) for config_path in config_paths if not config_path.exists()
    ]
    if missing_configs:
        raise FileNotFoundError(
            "Missing scenario config file(s): " + ", ".join(missing_configs)
        )

    comparison_frames: list[pd.DataFrame] = []

    for config_path in config_paths:
        scenario_name = _scenario_name_from_config(config_path)
        scenario_output_dir = output_dir / scenario_name

        print(f"Running scenario: {scenario_name}")
        comparison_rows = _run_single_scenario(
            config_path=config_path,
            scenario_output_dir=scenario_output_dir,
        )
        comparison_frames.append(comparison_rows)

    comparison = pd.concat(comparison_frames, ignore_index=True)
    _write_comparison_outputs(comparison=comparison, output_dir=output_dir)

    print()
    print("FedNDT-RRM scenario suite completed successfully")
    print(f"Output directory: {output_dir}")
    print()
    print(
        comparison[
            [
                "scenario",
                "strategy",
                "avg_latency_ms",
                "p95_latency_ms",
                "p99_latency_ms",
                "sla_violation_rate",
                "severe_sla_violation_rate",
                "avg_latency_excess_ms",
                "resource_fairness_jain",
                "throughput_fairness_jain",
                "overhead_reduction_ratio",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
