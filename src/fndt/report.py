"""Turn raw results into statistics tables, figures and REPORT.md.

Usage: python -m fndt.report --run results/v2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from fndt import stats  # noqa: E402
from fndt.simulator import STRATEGIES  # noqa: E402

LABEL = {s.name: s.label for s in STRATEGIES}
# Fixed categorical order (validated reference palette, light mode); colour follows the strategy.
COLOR = {
    "fndt": "#2a78d6",
    "fndt_no_incentive": "#eb6834",
    "centralized": "#1baf7a",
    "ndt_only": "#eda100",
    "fl_only": "#e87ba4",
    "greedy": "#008300",
    "static": "#6250d6",
}
ORDER = ["static", "greedy", "centralized", "fl_only", "ndt_only", "fndt_no_incentive", "fndt"]
LABEL_COLOR = {"Strong improvement": "#0f6e2e", "Modest improvement": "#6fbf73", "Neutral": "#d9d9d6", "Regression": "#c0392b"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
METRIC_TITLE = {
    "mean_latency_ms": "Mean latency (ms)",
    "p95_latency_ms": "p95 latency (ms)",
    "p99_latency_ms": "p99 latency (ms)",
    "sla_violation_rate": "SLA violation rate",
    "drop_rate": "Drop rate",
    "forecast_fidelity": "Forecast fidelity (1 − WAPE)",
    "twin_fidelity": "Twin fidelity (1 − NMAE)",
    "fl_final_loss": "FL validation loss",
    "participation_rate": "Participation rate",
    "overhead_mb": "Control overhead (MB/day)",
    "throughput_mbps": "Throughput (Mbit/s)",
    "jain_satisfaction": "Jain fairness (served/offered)",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 300, "figure.dpi": 110,
    "legend.frameon": False,
})


def _save(fig, out: Path, name: str) -> None:
    fig.savefig(out / f"{name}.png", bbox_inches="tight")
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_scenarios(df: pd.DataFrame, out: Path, metric: str) -> None:
    scen = list(dict.fromkeys(df.scenario))
    fig, axes = plt.subplots(3, 3, figsize=(10, 8.2), sharex=False)
    for ax, sc in zip(axes.ravel(), scen):
        g = df[df.scenario == sc].groupby("strategy")[metric]
        m, s, n = g.mean(), g.std(), g.count()
        half = 1.96 * s / np.sqrt(n)
        for i, k in enumerate(ORDER):
            ax.errorbar(m[k], i, xerr=half[k], fmt="o", ms=5, color=COLOR[k], elinewidth=1.5, capsize=0)
        ax.set_yticks(range(len(ORDER)), [LABEL[k] for k in ORDER])
        ax.set_title(sc.replace("_", " "), fontsize=9, color=INK, loc="left")
        ax.grid(axis="y", visible=False)
        if metric.endswith("_ms") and m.max() / max(m.min(), 1e-9) > 8:
            ax.set_xscale("log")
    fig.suptitle(f"{METRIC_TITLE[metric]} by scenario (mean, 95% CI, 30 seeds)", x=0.01, ha="left", color=INK)
    fig.tight_layout()
    _save(fig, out, f"scenarios_{metric}")


def fig_label_grid(cmp: pd.DataFrame, out: Path, metric: str = "mean_latency_ms") -> None:
    c = cmp[cmp.metric == metric].copy()
    c["pair"] = c.focal.map(LABEL) + " vs " + c.reference.map(LABEL)
    pairs = list(dict.fromkeys(c.pair))
    scen = list(dict.fromkeys(c.scenario))
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(pairs) + 1.6))
    for i, p in enumerate(pairs):
        for j, s in enumerate(scen):
            r = c[(c.pair == p) & (c.scenario == s)]
            if r.empty:
                continue
            r = r.iloc[0]
            ax.add_patch(plt.Rectangle((j, i), 0.96, 0.92, color=LABEL_COLOR[r.label]))
            ink = "white" if r.label in ("Strong improvement", "Regression") else INK
            ax.text(j + 0.48, i + 0.46, f"{r.improvement_pct:+.1f}%", ha="center", va="center", fontsize=8, color=ink)
    ax.set_xlim(0, len(scen))
    ax.set_ylim(len(pairs), 0)
    ax.set_xticks(np.arange(len(scen)) + 0.48, [s.replace("_", "\n") for s in scen], fontsize=7.5)
    ax.set_yticks(np.arange(len(pairs)) + 0.46, pairs)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=v) for v in LABEL_COLOR.values()]
    ax.legend(handles, LABEL_COLOR.keys(), ncol=4, loc="upper left", bbox_to_anchor=(0, -0.12), fontsize=8)
    ax.set_title(f"Claim-safe labels: {METRIC_TITLE[metric]} (Holm-adjusted Wilcoxon, bootstrap CI)", loc="left", color=INK)
    _save(fig, out, f"labels_{metric}")


def fig_sweep(sw: pd.DataFrame, out: Path, axis: str, metric: str, xlabel: str) -> None:
    d = sw[sw.axis == axis].copy()
    if d.empty:
        return
    d["value"] = d["value"].astype(float)
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for k in ORDER:
        g = d[d.strategy == k].groupby("value")[metric]
        if g.ngroups == 0:
            continue
        m, s, n = g.mean(), g.std(), g.count()
        half = 1.96 * s / np.sqrt(n)
        ax.plot(m.index, m.values, color=COLOR[k], lw=2, marker="o", ms=4, label=LABEL[k])
        ax.fill_between(m.index, m - half, m + half, color=COLOR[k], alpha=0.12, lw=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(METRIC_TITLE[metric])
    if metric.endswith("_ms"):
        ax.set_yscale("log")
    ax.legend(fontsize=7, ncol=2)
    _save(fig, out, f"sweep_{axis}_{metric}")


def fig_abg(sw: pd.DataFrame, out: Path, base: str, metric: str = "mean_latency_ms") -> pd.DataFrame:
    d = sw[sw.axis == f"alpha_beta_gamma:{base}"]
    if d.empty:
        return pd.DataFrame()
    w = d.pivot_table(index=["value", "seed"], columns="strategy", values=metric).reset_index()
    w["impr"] = stats.improvement_pct(w["fndt"].to_numpy(), w["fndt_no_incentive"].to_numpy(), metric)
    agg = w.groupby("value")["impr"].agg(["mean", "std", "count"]).reset_index()
    abg = agg["value"].str.split("/", expand=True).astype(float)
    agg["alpha"], agg["beta"], agg["gamma"] = abg[0], abg[1], abg[2]
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    lim = max(abs(agg["mean"]).max(), 0.5)
    sc = ax.scatter(agg.alpha, agg.beta, c=agg["mean"], cmap="RdBu", vmin=-lim, vmax=lim, s=420, marker="s", edgecolor="white")
    for _, r in agg.iterrows():
        ax.text(r.alpha, r.beta, f"{r['mean']:+.1f}", ha="center", va="center", fontsize=7, color=INK)
    ax.set_xlabel("α (quality weight)")
    ax.set_ylabel("β (cost weight);  γ = 1 − α − β")
    ax.set_xlim(-0.15, 1.15)
    ax.set_ylim(-0.15, 1.15)
    fig.colorbar(sc, ax=ax, label="Latency improvement vs FNDT w/o incentive (%)")
    ax.set_title(f"Incentive weights, {base.replace('_', ' ')}", loc="left", fontsize=9)
    _save(fig, out, f"abg_{base}")
    return agg


def fig_tradeoff(df: pd.DataFrame, out: Path, scenario: str = "baseline") -> None:
    d = df[df.scenario == scenario].groupby("strategy")[["mean_latency_ms", "overhead_mb"]].mean()
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for k in ORDER:
        x = max(d.loc[k, "overhead_mb"], 1e-3)
        ax.scatter(x, d.loc[k, "mean_latency_ms"], color=COLOR[k], s=60, zorder=3, edgecolor="white", linewidth=1.5)
        ax.annotate(LABEL[k], (x, d.loc[k, "mean_latency_ms"]), xytext=(5, 4), textcoords="offset points", fontsize=7.5, color=INK)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Control-plane overhead (MB/day, log; Static shown at 0.001)")
    ax.set_ylabel("Mean latency (ms, log)")
    ax.set_title(f"Latency vs overhead, {scenario}", loc="left", fontsize=9)
    _save(fig, out, f"tradeoff_{scenario}")


def _fmt(x, nd=2):
    return "–" if pd.isna(x) else f"{x:.{nd}f}"


def write_report(run: Path, df: pd.DataFrame, sw: pd.DataFrame | None, cmp: pd.DataFrame, ni: pd.DataFrame, fr: pd.DataFrame, abg: dict) -> None:
    man = json.loads((run / "manifest.json").read_text())
    L = []
    L.append("# FNDT simulator v2 — statistical report\n")
    L.append(f"Generated from `{run.name}`; commit `{man['git_commit'][:10]}`; Python {man['python']}; "
             f"confirmatory seeds {man['confirmatory_seeds'][0]}–{man['confirmatory_seeds'][1]} (paired across strategies).\n")
    L.append("Method: two-sided Wilcoxon signed-rank tests on paired seeds; Holm correction within each scenario "
             "(primary and secondary metric families separately); 95% percentile-bootstrap CI of the mean paired improvement "
             "(10,000 resamples); Cohen's d_z and Vargha–Delaney A12; labels follow the paper's claim-safe tiers and "
             "require p_Holm < 0.05 with a CI excluding zero.\n")
    L.append("## Label counts (primary metrics)\n")
    prim = cmp[cmp.primary]
    t = prim.groupby(["hypothesis", "focal", "reference", "label"]).size().unstack(fill_value=0)
    L.append(t.to_markdown() + "\n")
    L.append("## Mean latency, all scenarios (improvement of focal over reference)\n")
    m = cmp[cmp.metric == "mean_latency_ms"]
    rows = ["| Scenario | " + " | ".join(f"{LABEL[f]} vs {LABEL[r]}" for f, r, _ in stats.COMPARISONS) + " |",
            "|---|" + "---|" * len(stats.COMPARISONS)]
    for sc in dict.fromkeys(m.scenario):
        cells = []
        for f, r, _ in stats.COMPARISONS:
            x = m[(m.scenario == sc) & (m.focal == f) & (m.reference == r)]
            cells.append("–" if x.empty else f"{x.improvement_pct.iloc[0]:+.1f}% [{x.ci_low.iloc[0]:+.1f}, {x.ci_high.iloc[0]:+.1f}] {x.label.iloc[0]}")
        rows.append(f"| {sc} | " + " | ".join(cells) + " |")
    L.append("\n".join(rows) + "\n")
    L.append("## H2: non-inferiority of FNDT to Centralized (mean latency, margin 5%)\n")
    L.append(ni.round(3).to_markdown(index=False) + "\n")
    L.append("## Friedman test and mean ranks (mean latency; rank 1 = best)\n")
    L.append(fr.round(4).to_markdown(index=False) + "\n")
    L.append("## Descriptive statistics (mean ± SD over seeds)\n")
    keys = ["mean_latency_ms", "p95_latency_ms", "sla_violation_rate", "drop_rate", "forecast_fidelity", "twin_fidelity", "overhead_mb", "raw_records_exposed"]
    for sc in dict.fromkeys(df.scenario):
        g = df[df.scenario == sc].groupby("strategy")[keys]
        mean, sd = g.mean(), g.std()
        L.append(f"### {sc}\n")
        hdr = "| Strategy | " + " | ".join(METRIC_TITLE.get(k, k) for k in keys) + " |"
        L.append(hdr)
        L.append("|---|" + "---|" * len(keys))
        for k in ORDER:
            L.append(f"| {LABEL[k]} | " + " | ".join(f"{_fmt(mean.loc[k, c], 3)} ± {_fmt(sd.loc[k, c], 3)}" for c in keys) + " |")
        L.append("")
    if abg:
        L.append("## Incentive-weight sensitivity (α, β, γ)\n")
        for base, agg in abg.items():
            L.append(f"### {base}\n")
            L.append(agg[["alpha", "beta", "gamma", "mean", "std", "count"]].rename(columns={"mean": "latency improvement % (mean)", "std": "sd"}).round(3).to_markdown(index=False) + "\n")
    L.append("## Files\n")
    L.append("- `raw/main.csv`, `raw/sweeps.csv`: one row per scenario × seed × strategy\n- `stats/comparisons.csv`: every test with raw and Holm p-values, CIs and effect sizes\n- `figures/`: PNG (300 dpi) and vector PDF\n- `manifest.json`: provenance\n")
    (run / "REPORT.md").write_text("\n".join(L), encoding="utf-8")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    args = ap.parse_args(argv)
    run = Path(args.run)
    figs, st = run / "figures", run / "stats"
    figs.mkdir(exist_ok=True)
    st.mkdir(exist_ok=True)
    df = pd.read_csv(run / "raw" / "main.csv")
    sw = pd.read_csv(run / "raw" / "sweeps.csv") if (run / "raw" / "sweeps.csv").exists() else None

    cmp = stats.compare(df)
    cmp.to_csv(st / "comparisons.csv", index=False)
    ni = stats.non_inferiority(df)
    ni.to_csv(st / "non_inferiority.csv", index=False)
    fr = stats.friedman_ranks(df, "mean_latency_ms")
    fr.to_csv(st / "friedman_mean_latency.csv", index=False)
    stats.describe(df, stats.PRIMARY_METRICS + stats.SECONDARY_METRICS).to_csv(st / "descriptive.csv", index=False)

    for metric in ("mean_latency_ms", "p95_latency_ms", "sla_violation_rate", "twin_fidelity", "forecast_fidelity"):
        fig_scenarios(df, figs, metric)
    for metric in ("mean_latency_ms", "sla_violation_rate"):
        fig_label_grid(cmp, figs, metric)
    fig_tradeoff(df, figs)
    abg = {}
    if sw is not None:
        sw.to_csv(st / "sweeps_raw_copy.csv", index=False)
        for axis, xl in (("traffic_pressure", "Traffic pressure (× baseline load)"), ("report_noise", "Report noise (std)"),
                         ("telemetry_staleness", "Telemetry staleness (slots)"), ("noniid", "Non-IID severity")):
            fig_sweep(sw, figs, axis, "mean_latency_ms", xl)
        fig_sweep(sw, figs, "elasticity", "participation_rate", "Participation elasticity")
        fig_sweep(sw, figs, "elasticity", "mean_latency_ms", "Participation elasticity")
        for base in ("baseline", "low_quality_contributors"):
            agg = fig_abg(sw, figs, base)
            if not agg.empty:
                abg[base] = agg
                agg.to_csv(st / f"abg_{base}.csv", index=False)
        sens = sw.groupby(["axis", "value", "strategy"])[["mean_latency_ms", "sla_violation_rate", "forecast_fidelity", "twin_fidelity", "participation_rate", "fl_final_loss"]].agg(["mean", "std"])
        sens.to_csv(st / "sweeps_summary.csv")
    write_report(run, df, sw, cmp, ni, fr, abg)
    print(f"report written to {run / 'REPORT.md'}")


if __name__ == "__main__":
    main()
