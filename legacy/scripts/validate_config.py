from __future__ import annotations

import argparse

from fedndt_rrm.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a FedNDT-RRM YAML configuration file."
    )
    parser.add_argument(
        "--config",
        default="configs/peak_traffic.yaml",
        help="Path to simulation config YAML file.",
    )

    args = parser.parse_args()
    config = load_config(args.config)

    print("FedNDT-RRM config loaded successfully")
    print(f"Config path: {args.config}")
    print(f"Random seed: {config.simulation.random_seed}")
    print(f"Time steps: {config.simulation.time_steps}")
    print(f"Edge/RAN nodes: {config.network.num_edge_nodes}")
    print(f"Users: {config.network.num_users}")
    print(f"Total resource units: {config.network.total_resource_units}")
    print(f"SLA threshold: {config.network.sla_latency_threshold_ms} ms")
    print(f"Traffic profile: {config.traffic.profile}")
    print(f"Incentive enabled: {config.incentive.enabled}")
    print(f"Stress enabled: {config.stress.enabled}")

    if config.stress.enabled:
        print(f"Overloaded node: {config.stress.overloaded_edge_node_id}")
        print(f"Overload multiplier: {config.stress.overload_multiplier}")
        print(f"Mobility shift probability: {config.stress.mobility_shift_probability}")
        print(f"Unreliable node: {config.stress.unreliable_edge_node_id}")
        print(f"Stale update probability: {config.stress.stale_update_probability}")
        print(f"Report noise probability: {config.stress.report_noise_probability}")
        print(f"Greedy delay steps: {config.stress.greedy_observation_delay_steps}")


if __name__ == "__main__":
    main()
