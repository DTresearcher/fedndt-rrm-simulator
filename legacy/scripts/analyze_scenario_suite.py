from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from fedndt_rrm.scenario_analysis import (
    BASELINE_STRATEGIES,
    build_key_claim_summary,
    build_wide_improvement_table,
    compute_strategy_improvements,
)


def _write_latex_table(
    frame: pd.DataFrame,
    path: Path,
    *,
    caption: str,
    label: str,
) -> None:
    latex_table = frame.to_latex(
        index=False,
        float_format="%.2f",
        caption=caption,
        label=label,
    )
    path.write_text(latex_table, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze FedNDT-RRM scenario-suite comparison outputs."
    )
    parser.add_argument(
        "--comparison",
        default="results/scenario_suite/scenario_comparison.csv",
        help="Path to scenario_comparison.csv produced by run_scenario_suite.py.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/scenario_suite_analysis",
        help="Directory where analysis outputs will be saved.",
    )

    args = parser.parse_args()

    comparison_path = Path(args.comparison)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not comparison_path.exists():
        raise FileNotFoundError(
            f"Scenario comparison file not found: {comparison_path}. "
            "Run: uv run python scripts/run_scenario_suite.py"
        )

    comparison = pd.read_csv(comparison_path)
    improvements = compute_strategy_improvements(comparison)

    improvements.to_csv(
        output_dir / "strategy_improvements_long.csv",
        index=False,
    )

    key_claim_summary = build_key_claim_summary(improvements)
    key_claim_summary.to_csv(
        output_dir / "key_claim_summary.csv",
        index=False,
    )

    for baseline_strategy in BASELINE_STRATEGIES:
        wide_table = build_wide_improvement_table(
            improvements,
            baseline_strategy=baseline_strategy,
        )

        csv_path = output_dir / f"fedndt_vs_{baseline_strategy}_improvements.csv"
        tex_path = output_dir / f"fedndt_vs_{baseline_strategy}_improvements.tex"

        wide_table.to_csv(csv_path, index=False)

        _write_latex_table(
            wide_table,
            tex_path,
            caption=(
                f"Percentage improvement of FedNDT-Incentive compared with "
                f"{baseline_strategy} across scenario-suite experiments."
            ),
            label=f"tab:fedndt-vs-{baseline_strategy}-improvements",
        )

    print("FedNDT-RRM scenario-suite analysis completed successfully")
    print(f"Input comparison: {comparison_path}")
    print(f"Output directory: {output_dir}")
    print()
    print("Generated files:")
    for path in sorted(output_dir.glob("*")):
        print(f"- {path}")

    print()
    print("FedNDT vs greedy improvement summary:")
    greedy_table = pd.read_csv(output_dir / "fedndt_vs_greedy_improvements.csv")
    print(greedy_table.to_string(index=False))

    print()
    print("FedNDT vs static improvement summary:")
    static_table = pd.read_csv(output_dir / "fedndt_vs_static_improvements.csv")
    print(static_table.to_string(index=False))


if __name__ == "__main__":
    main()
