from __future__ import annotations

import argparse
import json
from pathlib import Path


from fedndt_rrm.config import load_config
from fedndt_rrm.digital_twin import add_demand_predictions, build_local_digital_twins
from fedndt_rrm.scenario import generate_synthetic_telemetry


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local Network Digital Twin states.")
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

    telemetry_path = output_dir / "raw_telemetry.csv"
    ndt_state_path = output_dir / "ndt_state.csv"
    summary_path = output_dir / "ndt_summary.json"

    telemetry.to_csv(telemetry_path, index=False)
    ndt_state.to_csv(ndt_state_path, index=False)

    summary = {
        "telemetry": telemetry_summary.to_dict(),
        "ndt_state": {
            "rows": int(len(ndt_state)),
            "avg_total_demand": round(float(ndt_state["total_demand"].mean()), 4),
            "avg_congestion_risk": round(float(ndt_state["congestion_risk"].mean()), 4),
            "avg_prediction_error_abs": round(
                float(ndt_state["prediction_error_abs"].mean()), 4
            ),
            "max_congestion_risk": round(float(ndt_state["congestion_risk"].max()), 4),
        },
    }

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("Local Network Digital Twin states generated successfully")
    print(f"Raw telemetry CSV: {telemetry_path}")
    print(f"NDT state CSV: {ndt_state_path}")
    print(f"NDT summary JSON: {summary_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
