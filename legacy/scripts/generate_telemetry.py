from __future__ import annotations

import argparse
import json
from pathlib import Path

from fedndt_rrm.config import load_config
from fedndt_rrm.scenario import generate_synthetic_telemetry


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic Edge/RAN telemetry.")
    parser.add_argument(
        "--config",
        default="configs/peak_traffic.yaml",
        help="Path to simulation config YAML file.",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory where telemetry outputs will be saved.",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)
    telemetry, summary = generate_synthetic_telemetry(config)

    telemetry_path = output_dir / "raw_telemetry.csv"
    summary_path = output_dir / "telemetry_summary.json"

    telemetry.to_csv(telemetry_path, index=False)

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(summary.to_dict(), file, indent=2)

    print("Synthetic telemetry generated successfully")
    print(f"Telemetry CSV: {telemetry_path}")
    print(f"Summary JSON: {summary_path}")
    print(json.dumps(summary.to_dict(), indent=2))


if __name__ == "__main__":
    main()
