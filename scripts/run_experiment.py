from __future__ import annotations

import argparse
import json
from pathlib import Path

from fedndt_rrm.config import load_config
from fedndt_rrm.digital_twin import add_demand_predictions, build_local_digital_twins
from fedndt_rrm.incentive_engine import add_incentive_scores
from fedndt_rrm.metrics import evaluate_allocations
from fedndt_rrm.resource_allocator import allocate_resources
from fedndt_rrm.scenario import generate_synthetic_telemetry


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FedNDT-RRM simulation.")
    parser.add_argument(
        "--config",
        default="configs/peak_traffic.yaml",
        help="Path to simulation config YAML file.",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory where outputs will be saved.",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)

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

    telemetry.to_csv(output_dir / "raw_telemetry.csv", index=False)
    ndt_state.to_csv(output_dir / "ndt_state.csv", index=False)
    allocations.to_csv(output_dir / "allocations.csv", index=False)
    per_step_metrics.to_csv(output_dir / "metrics.csv", index=False)
    summary_metrics.to_csv(output_dir / "summary_metrics.csv", index=False)

    summary = {
        "telemetry": telemetry_summary.to_dict(),
        "simulation": {
            "time_steps": config.simulation.time_steps,
            "num_edge_nodes": config.network.num_edge_nodes,
            "num_users": config.network.num_users,
            "total_resource_units": config.network.total_resource_units,
            "sla_latency_threshold_ms": config.network.sla_latency_threshold_ms,
        },
        "summary_metrics": summary_metrics.to_dict(orient="records"),
    }

    with (output_dir / "summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("FedNDT-RRM simulation completed successfully")
    print(f"Output directory: {output_dir}")
    print()
    print(summary_metrics.to_string(index=False))


if __name__ == "__main__":
    main()
