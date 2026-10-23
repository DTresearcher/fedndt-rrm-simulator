from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_bar_chart(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    title: str,
    ylabel: str,
    output_path: Path,
) -> None:
    plt.figure(figsize=(7, 4))
    plt.bar(data[x_column], data[y_column])
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel("Strategy")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def save_line_chart(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    group_column: str,
    title: str,
    ylabel: str,
    output_path: Path,
) -> None:
    plt.figure(figsize=(8, 4.5))

    for group_name, group_df in data.groupby(group_column):
        group_df = group_df.sort_values(x_column)
        plt.plot(group_df[x_column], group_df[y_column], label=str(group_name))

    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel("Simulation Time Step")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def main() -> None:
    results_dir = Path("results")
    figures_dir = results_dir / "figures"
    paper_figures_dir = Path("paper_assets") / "figures"

    figures_dir.mkdir(parents=True, exist_ok=True)
    paper_figures_dir.mkdir(parents=True, exist_ok=True)

    metrics = pd.read_csv(results_dir / "metrics.csv")
    summary = pd.read_csv(results_dir / "summary_metrics.csv")

    save_bar_chart(
        data=summary,
        x_column="strategy",
        y_column="avg_latency_ms",
        title="Average Latency by Allocation Strategy",
        ylabel="Average Latency (ms)",
        output_path=figures_dir / "avg_latency_comparison.png",
    )

    save_bar_chart(
        data=summary,
        x_column="strategy",
        y_column="p95_latency_ms",
        title="95th Percentile Latency by Allocation Strategy",
        ylabel="P95 Latency (ms)",
        output_path=figures_dir / "p95_latency_comparison.png",
    )

    save_bar_chart(
        data=summary,
        x_column="strategy",
        y_column="sla_violation_rate",
        title="SLA Violation Rate by Allocation Strategy",
        ylabel="SLA Violation Rate",
        output_path=figures_dir / "sla_violation_rate.png",
    )

    save_bar_chart(
        data=summary,
        x_column="strategy",
        y_column="avg_resource_utilization",
        title="Average Resource Utilization by Strategy",
        ylabel="Resource Utilization",
        output_path=figures_dir / "resource_utilization.png",
    )

    time_series = (
        metrics.groupby(["time_step", "strategy"])
        .agg(avg_latency_ms=("latency_ms", "mean"))
        .reset_index()
    )

    save_line_chart(
        data=time_series,
        x_column="time_step",
        y_column="avg_latency_ms",
        group_column="strategy",
        title="Average Latency Over Simulation Time",
        ylabel="Average Latency (ms)",
        output_path=figures_dir / "latency_over_time.png",
    )

    for figure in figures_dir.glob("*.png"):
        target = paper_figures_dir / figure.name
        target.write_bytes(figure.read_bytes())

    print("Figures generated successfully")
    print(f"Results figures: {figures_dir}")
    print(f"Paper figures: {paper_figures_dir}")


if __name__ == "__main__":
    main()
