from __future__ import annotations

from fedndt_rrm.config import load_config


def main() -> None:
    config = load_config("configs/peak_traffic.yaml")

    print("FedNDT-RRM config loaded successfully")
    print(f"Time steps: {config.simulation.time_steps}")
    print(f"Edge/RAN nodes: {config.network.num_edge_nodes}")
    print(f"Users: {config.network.num_users}")
    print(f"SLA threshold: {config.network.sla_latency_threshold_ms} ms")


if __name__ == "__main__":
    main()
