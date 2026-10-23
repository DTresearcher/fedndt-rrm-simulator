"""Turn raw results into statistics tables, figures and REPORT.md.

Usage: python -m fndt.report --run results
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
KIND = {s.name: s.kind for s in STRATEGIES}
# Fixed categorical order (validated reference palette, light mode). Colour follows the strategy;
# the two diagnostic arms reuse their parent's hue with hollow markers and dashed lines.
COLOR = {
    "fndt": "#2a78d6",
    "fndt_no_incentive": "#eb6834",
    "centralized": "#1baf7a",
    "ndt_only": "#eda100",
    "fl_only": "#e87ba4",
    "fl_state": "#e87ba4",
    "greedy": "#008300",
    "greedy_sr": "#008300",
    "static": "#6250d6",
}
HOLLOW = {"fl_state", "greedy_sr"}
ORDER = ["static", "greedy", "greedy_sr", "centralized", "fl_only", "fl_state", "ndt_only", "fndt_no_incentive", "fndt"]
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
    "forecast_loss_oos": "Out-of-sample forecast loss",
    "participation_rate": "Participation rate",
    "overhead_mb": "Control overhead (MB/day)",
    "throughput_mbps": "Throughput (Mbit/s)",
    "fl_energy_j": "FL device energy (J/day)",
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


def _marker(k):
    return {"mfc": "white" if k in HOLLOW else COLOR[k], "mec": COLOR[k], "mew": 1.6}


def _pair_name(f, r):
    return f"{LABEL[f]} vs {LABEL[r]}"


def fig_scenarios(df: pd.DataFrame, out: Path, metric: str) -> None:
    scen = list(dict.fromkeys(df.scenario))
    ncol = 3
    nrow = int(np.ceil(len(scen) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(10.5, 2.75 * nrow))
    present = [k for k in ORDER if k in set(df.strategy)]
    for ax in axes.ravel()[len(scen):]:
        ax.axis("off")
    for ax, sc in zip(axes.ravel(), scen):
        g = df[df.scenario == sc].groupby("strategy")[metric]
        m, s, n = g.mean(), g.std(), g.count()
        half = 1.96 * s / np.sqrt(n)
        ks = [k for k in present if np.isfinite(m.get(k, np.nan))]
        for i, k in enumerate(ks):
            ax.errorbar(m[k], i, xerr=half[k], fmt="o", ms=5, color=COLOR[k], elinewidth=1.4, capsize=0, **_marker(k))
        ax.set_yticks(range(len(ks)), [LABEL[k] for k in ks], fontsize=7.5)
        ax.set_title(sc.replace("_", " "), fontsize=9, color=INK, loc="left")
        ax.grid(axis="y", visible=False)
        if metric.endswith("_ms") and m[ks].max() / max(m[ks].min(), 1e-9) > 8:
            ax.set_xscale("log")
    fig.suptitle(f"{METRIC_TITLE[metric]} by scenario (mean and 95% CI across 30 seeds; tests are paired, see the forest plot)",
                 x=0.01, ha="left", color=INK, fontsize=9.5)
    fig.tight_layout()
    _save(fig, out, f"scenarios_{metric}")


def fig_label_grid(cmp: pd.DataFrame, out: Path, metric: str = "mean_latency_ms") -> None:
    c = cmp[cmp.metric == metric].copy()
    c["pair"] = [_pair_name(f, r) for f, r in zip(c.focal, c.reference)]
    pairs = [_pair_name(f, r) for f, r, _ in stats.COMPARISONS]
    scen = list(dict.fromkeys(c.scenario))
    fig, ax = plt.subplots(figsize=(11, 0.5 * len(pairs) + 1.7))
    for i, p in enumerate(pairs):
        for j, s in enumerate(scen):
            r = c[(c.pair == p) & (c.scenario == s)]
            if r.empty:
                continue
            r = r.iloc[0]
            ax.add_patch(plt.Rectangle((j, i), 0.96, 0.92, color=LABEL_COLOR[r.label]))
            ink = "white" if r.label in ("Strong improvement", "Regression") else INK
            ax.text(j + 0.48, i + 0.46, f"{r.improvement_pct:+.1f}%", ha="center", va="center", fontsize=7.5, color=ink)
    ax.set_xlim(0, len(scen))
    ax.set_ylim(len(pairs), 0)
    ax.set_xticks(np.arange(len(scen)) + 0.48, [s.replace("_", "\n") for s in scen], fontsize=7)
    ax.set_yticks(np.arange(len(pairs)) + 0.46, pairs, fontsize=8)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=v) for v in LABEL_COLOR.values()]
    ax.legend(handles, LABEL_COLOR.keys(), ncol=4, loc="upper left", bbox_to_anchor=(0, -0.13), fontsize=8)
    ax.set_title(f"Claim-safe labels, {METRIC_TITLE[metric].lower()} (relative difference of means; Wilcoxon + Holm; paired bootstrap CI)",
                 loc="left", color=INK, fontsize=9.5)
    _save(fig, out, f"labels_{metric}")


def fig_forest(cmp: pd.DataFrame, out: Path, metric: str = "mean_latency_ms") -> None:
    """Paired differences: improvement of the focal arm with its 95% paired bootstrap CI."""
    c = cmp[cmp.metric == metric]
    comps = [x for x in stats.COMPARISONS if x[1] != "static"]
    scen = list(dict.fromkeys(c.scenario))
    ncol = 4
    nrow = int(np.ceil(len(comps) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(11, 3.1 * nrow), sharey=True)
    for ax in axes.ravel()[len(comps):]:
        ax.axis("off")
    for ax, (f, r, hyp) in zip(axes.ravel(), comps):
        sub = c[(c.focal == f) & (c.reference == r)].set_index("scenario").reindex(scen)
        y = np.arange(len(scen))
        colors = [LABEL_COLOR[x] if x != "Neutral" else MUTED for x in sub.label]
        ax.axvline(0, color=MUTED, lw=0.8)
        ax.axvspan(-stats.MODEST, stats.MODEST, color=GRID, alpha=0.5, lw=0)
        ax.hlines(y, sub.ci_low, sub.ci_high, colors=colors, lw=2)
        ax.scatter(sub.improvement_pct, y, c=colors, s=18, zorder=3)
        ax.set_yticks(y, [s.replace("_", " ") for s in scen], fontsize=7)
        ax.invert_yaxis()
        ax.set_title(_pair_name(f, r), fontsize=8, loc="left", color=INK)
        ax.set_xlabel("improvement (%)", fontsize=7.5)
        lim = np.nanmax(np.abs(sub[["ci_low", "ci_high"]].to_numpy()))
        ax.set_xlim(-max(lim, 8) * 1.1, max(lim, 8) * 1.1)
    fig.suptitle(f"Paired differences, {METRIC_TITLE[metric].lower()}: positive = first-named arm better; shaded band = ±5% (Neutral zone)",
                 x=0.01, ha="left", fontsize=9.5, color=INK)
    fig.tight_layout()
    _save(fig, out, f"forest_{metric}")


def fig_sweep(sw: pd.DataFrame, out: Path, axis: str, metric: str, xlabel: str) -> None:
    d = sw[sw.axis == axis].copy()
    if d.empty:
        return
    d["value"] = d["value"].astype(float)
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    for k in ORDER:
        g = d[d.strategy == k].groupby("value")[metric]
        if g.ngroups == 0 or not np.isfinite(g.mean()).any():
            continue
        m, s, n = g.mean(), g.std(), g.count()
        half = 1.96 * s / np.sqrt(n)
        ax.plot(m.index, m.values, color=COLOR[k], lw=1.8, ls="--" if k in HOLLOW else "-", marker="o", ms=4, label=LABEL[k], **_marker(k))
        ax.fill_between(m.index, m - half, m + half, color=COLOR[k], alpha=0.08, lw=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(METRIC_TITLE[metric])
    if metric.endswith("_ms") and d[metric].max() / max(d[metric].min(), 1e-9) > 8:
        ax.set_yscale("log")
    ax.legend(fontsize=6.8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    _save(fig, out, f"sweep_{axis}_{metric}")


def abg_table(sw: pd.DataFrame, base: str) -> pd.DataFrame:
    d = sw[sw.axis == f"alpha_beta_gamma:{base}"]
    if d.empty:
        return pd.DataFrame()
    rows = []
    for value, g in d.groupby("value"):
        w = g.pivot(index="seed", columns="strategy")
        f, r = w["mean_latency_ms"]["fndt"].to_numpy(), w["mean_latency_ms"]["fndt_no_incentive"].to_numpy()
        lo, hi = stats.paired_bootstrap_ratio(f, r, "mean_latency_ms", seed=3)
        a, b, c = (float(x) for x in value.split("/"))
        rows.append({
            "alpha": a, "beta": b, "gamma": c, "default": (a, b, c) == (0.5, 0.2, 0.3),
            "latency_improvement_pct": stats.ratio_of_means(f, r, "mean_latency_ms"), "ci_low": lo, "ci_high": hi,
            "oos_loss_fndt": w["forecast_loss_oos"]["fndt"].mean(), "oos_loss_no_incentive": w["forecast_loss_oos"]["fndt_no_incentive"].mean(),
            "participation_fndt": w["participation_rate"]["fndt"].mean(), "participation_no_incentive": w["participation_rate"]["fndt_no_incentive"].mean(),
            "energy_fndt_j": w["fl_energy_j"]["fndt"].mean(), "energy_no_incentive_j": w["fl_energy_j"]["fndt_no_incentive"].mean(),
            "reward_jain": w["reward_jain"]["fndt"].mean(), "n": len(f),
        })
    return pd.DataFrame(rows).sort_values(["alpha", "beta"])


def fig_abg(agg: pd.DataFrame, out: Path, base: str) -> None:
    fig, ax = plt.subplots(figsize=(4.8, 3.9))
    vals = agg["latency_improvement_pct"]
    lim = min(max(abs(vals).max(), 0.5), 25.0)
    sc = ax.scatter(agg.alpha, agg.beta, c=vals.clip(-lim, lim), cmap="RdBu", vmin=-lim, vmax=lim, s=430, marker="s",
                    edgecolor=np.where(agg["default"], INK, "white"), linewidth=np.where(agg["default"], 1.6, 0.8))
    for _, r in agg.iterrows():
        ink = "white" if abs(r.latency_improvement_pct) > 0.6 * lim else INK
        ax.text(r.alpha, r.beta, f"{r.latency_improvement_pct:+.1f}", ha="center", va="center", fontsize=6.8, color=ink)
    ax.set_xlabel("α (quality weight)")
    ax.set_ylabel("β (cost weight);  γ = 1 − α − β")
    ax.set_xlim(-0.15, 1.15)
    ax.set_ylim(-0.15, 1.15)
    fig.colorbar(sc, ax=ax, extend="both", label="Latency improvement vs FNDT w/o incentive (%)")
    ax.set_title(f"Incentive weights, {base.replace('_', ' ')} (outlined: default 0.5/0.2/0.3)", loc="left", fontsize=8.5)
    _save(fig, out, f"abg_{base}")


def fig_tradeoff(df: pd.DataFrame, out: Path, scenario: str = "baseline") -> None:
    d = df[df.scenario == scenario].groupby("strategy")[["mean_latency_ms", "overhead_mb"]].mean()
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    offsets = {"static": (6, -2), "greedy": (-40, 8), "greedy_sr": (8, 8), "centralized": (-30, 10), "fl_only": (-48, 12),
               "fl_state": (-20, -16), "ndt_only": (6, 18), "fndt_no_incentive": (12, 10), "fndt": (14, -12)}
    for k in ORDER:
        x = max(d.loc[k, "overhead_mb"], 1e-3)
        y = d.loc[k, "mean_latency_ms"]
        ax.plot(x, y, "o", ms=8, color=COLOR[k], zorder=3, **_marker(k))
        ax.annotate(LABEL[k], (x, y), xytext=offsets.get(k, (5, 4)), textcoords="offset points", fontsize=7, color=INK,
                    arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.5})
    ax.set_xscale("log")
    ax.set_yscale("log")
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo * 0.85, hi * 1.1)
    ax.set_xlabel("Control-plane overhead (MB/day, log; Static shown at 0.001)")
    ax.set_ylabel("Mean latency (ms, log)")
    ax.set_title(f"Latency vs overhead, {scenario}", loc="left", fontsize=9)
    _save(fig, out, f"tradeoff_{scenario}")


def sweep_paired(sw: pd.DataFrame) -> pd.DataFrame:
    """For every numeric sweep point: FNDT vs each other arm, relative difference of means and paired CI."""
    rows = []
    num = sw[~sw.axis.str.startswith("alpha")].copy()
    for (axis, value), g in num.groupby(["axis", "value"]):
        w = g.pivot(index="seed", columns="strategy", values="mean_latency_ms")
        if "fndt" not in w:
            continue
        for ref in w.columns:
            if ref == "fndt":
                continue
            f, r = w["fndt"].to_numpy(), w[ref].to_numpy()
            lo, hi = stats.paired_bootstrap_ratio(f, r, "mean_latency_ms", seed=5)
            rows.append({"axis": axis, "value": value, "reference": ref, "improvement_pct": stats.ratio_of_means(f, r, "mean_latency_ms"),
                         "ci_low": lo, "ci_high": hi, "n": len(f)})
    return pd.DataFrame(rows)


def _md(df: pd.DataFrame, digits: int = 3) -> str:
    return df.round(digits).to_markdown(index=False)


def write_report(run: Path, df, sw, cmp, ni, fr, calib, fid_bins, abg, swp) -> None:
    man = json.loads((run / "manifest.json").read_text())
    L = ["# FNDT simulator — statistical report\n"]
    L.append(f"Commit `{man['git_commit'][:10]}` · Python {man['python']} · confirmatory seeds "
             f"{man['confirmatory_seeds'][0]}–{man['confirmatory_seeds'][1]} (paired across strategies) · sweep seeds "
             f"{man['sweep_seeds'][0]}–{man['sweep_seeds'][1]}.\n")
    L.append("**Method.**\n")
    L.append("- **Effect.** The relative difference of means (positive = first-named arm better), with a 95% paired percentile bootstrap CI (10,000 resamples of seed pairs).")
    L.append("- **Test.** Two-sided Wilcoxon signed-rank test on the paired seeds.")
    L.append("- **Multiplicity.** Holm correction within each scenario, with the primary and secondary families corrected separately.")
    L.append("- **Labels.** Claim-safe tiers: Strong ≥ 15%, Modest 5–15%, Regression ≤ −5%. A label other than Neutral requires p_Holm < 0.05 and a CI that excludes 0. Rate metrics also require an absolute difference of at least 0.1 percentage point.")
    L.append("- **Sensitivity checks.** A global Holm family, and the mean of per-seed ratios as an alternative effect measure.\n")
    prim = cmp[cmp.primary]
    L.append("## Label counts, primary metrics (mean latency, p95, SLA violation, drop rate)\n")
    L.append(prim.groupby(["hypothesis", "label"]).size().unstack(fill_value=0).to_markdown() + "\n")
    changed = int((prim.label != prim.label_global_holm).sum())
    L.append(f"Global Holm over all {len(prim)} primary tests changes {changed} label(s).\n")
    mor_labels = [stats.claim_label(r.improvement_pct_mean_of_ratios, r.p_holm, r.ci_low, r.ci_high, r.metric, r.abs_diff) for r in prim.itertuples()]
    L.append(f"Using the mean of per-seed ratios instead of the ratio of means changes {int((np.array(mor_labels) != prim.label.to_numpy()).sum())} label(s).\n")
    L.append("## Mean latency per scenario (improvement [95% CI] label)\n")
    m = cmp[cmp.metric == "mean_latency_ms"]
    head = "| Scenario | " + " | ".join(_pair_name(f, r) for f, r, _ in stats.COMPARISONS) + " |"
    L += [head, "|---|" + "---|" * len(stats.COMPARISONS)]
    for sc in dict.fromkeys(m.scenario):
        cells = []
        for f, r, _ in stats.COMPARISONS:
            x = m[(m.scenario == sc) & (m.focal == f) & (m.reference == r)]
            cells.append("–" if x.empty else f"{x.improvement_pct.iloc[0]:+.1f}% [{x.ci_low.iloc[0]:+.1f}, {x.ci_high.iloc[0]:+.1f}] {x.label.iloc[0]}")
        L.append(f"| {sc} | " + " | ".join(cells) + " |")
    L.append("\n## H2: non-inferiority of FNDT to Centralized (mean latency, margin 5%)\n")
    L.append(_md(ni) + "\n")
    L.append("## Calibration and load (mean over seeds)\n")
    L.append(_md(calib) + "\n")
    L.append("## Twin fidelity by network utilisation (FNDT)\n")
    L.append(_md(fid_bins) + "\n")
    L.append("## Friedman test and mean ranks (mean latency; 1 = best)\n")
    L.append(_md(fr, 4) + "\n")
    L.append("## Descriptive statistics (mean ± SD over seeds)\n")
    keys = ["mean_latency_ms", "p95_latency_ms", "sla_violation_rate", "drop_rate", "forecast_fidelity", "twin_fidelity",
            "forecast_loss_oos", "participation_rate", "overhead_mb", "raw_records_exposed"]
    for sc in dict.fromkeys(df.scenario):
        g = df[df.scenario == sc].groupby("strategy")[keys]
        mean, sd = g.mean(), g.std()
        L.append(f"### {sc}\n")
        L += ["| Strategy | " + " | ".join(METRIC_TITLE.get(k, k) for k in keys) + " |", "|---|" + "---|" * len(keys)]
        for k in ORDER:
            L.append(f"| {LABEL[k]} | " + " | ".join("–" if pd.isna(mean.loc[k, c]) else f"{mean.loc[k, c]:.4g} ± {sd.loc[k, c]:.2g}" for c in keys) + " |")
        L.append("")
    if abg:
        L.append("## Incentive weights (α, β, γ): latency, model loss, participation, energy, reward fairness\n")
        for base, agg in abg.items():
            L.append(f"### {base}\n")
            L.append(_md(agg.drop(columns=["n"]), 4) + "\n")
    if swp is not None and not swp.empty:
        L.append("## Sensitivity sweeps: FNDT vs each arm (mean latency, relative difference of means [95% paired CI])\n")
        L.append(_md(swp.pivot_table(index=["axis", "value"], columns="reference", values="improvement_pct").reset_index(), 2) + "\n")
    L.append("## Files\n")
    L.append("- `raw/main.csv`, `raw/sweeps.csv`: one row per scenario × seed × strategy.")
    L.append("- `stats/comparisons.csv`: every test, with raw, Holm and global-Holm p-values, CIs and effect sizes.")
    L.append("- `stats/*.csv`: calibration, fidelity by utilisation, α/β/γ trade-offs, paired sweep CIs, descriptive statistics.")
    L.append("- `figures/`: PNG (300 dpi) and vector PDF.")
    L.append("- `manifest.json`: provenance.\n")
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
    sw = pd.read_csv(run / "raw" / "sweeps.csv", dtype={"value": str}) if (run / "raw" / "sweeps.csv").exists() else None

    cmp = stats.compare(df)
    cmp.to_csv(st / "comparisons.csv", index=False)
    ni = stats.non_inferiority(df)
    ni.to_csv(st / "non_inferiority.csv", index=False)
    fr = stats.friedman_ranks(df, "mean_latency_ms")
    fr.to_csv(st / "friedman_mean_latency.csv", index=False)
    stats.describe(df, stats.PRIMARY_METRICS + stats.SECONDARY_METRICS).to_csv(st / "descriptive.csv", index=False)
    calib = df[df.strategy.isin(["static", "fndt"])].groupby(["scenario", "strategy"], sort=False)[
        ["mean_site_util", "p95_site_util", "saturated_site_slots", "peak_network_util", "mean_latency_ms", "drop_rate"]].mean().reset_index()
    calib.to_csv(st / "calibration.csv", index=False)
    fid_bins = df[df.strategy == "fndt"].groupby("scenario", sort=False)[
        ["twin_fidelity", "twin_fidelity_util_lt50", "twin_fidelity_util_50to80", "twin_fidelity_util_ge80"]].mean().reset_index()
    fid_bins.to_csv(st / "twin_fidelity_by_utilisation.csv", index=False)

    for metric in ("mean_latency_ms", "p95_latency_ms", "sla_violation_rate", "twin_fidelity", "forecast_fidelity"):
        fig_scenarios(df, figs, metric)
    for metric in ("mean_latency_ms", "sla_violation_rate"):
        fig_label_grid(cmp, figs, metric)
    fig_forest(cmp, figs)
    fig_tradeoff(df, figs)
    abg, swp = {}, None
    if sw is not None:
        num = sw[~sw.axis.str.startswith("alpha")].copy()
        for axis, xl in (("traffic_pressure", "Traffic pressure (× baseline load)"), ("report_noise", "Report noise (std)"),
                         ("telemetry_staleness", "Telemetry staleness (slots)"), ("noniid", "Non-IID severity"),
                         ("service_variability", "Service-time SCV (twin assumes 1)")):
            fig_sweep(num, figs, axis, "mean_latency_ms", xl)
        fig_sweep(num, figs, "service_variability", "twin_fidelity", "Service-time SCV (twin assumes 1)")
        fig_sweep(num, figs, "elasticity", "participation_rate", "Participation elasticity")
        for base in ("baseline", "low_quality_contributors"):
            agg = abg_table(sw, base)
            if not agg.empty:
                abg[base] = agg
                agg.to_csv(st / f"abg_{base}.csv", index=False)
                fig_abg(agg, figs, base)
        swp = sweep_paired(sw)
        swp.to_csv(st / "sweeps_paired.csv", index=False)
        num.groupby(["axis", "value", "strategy"])[["mean_latency_ms", "sla_violation_rate", "forecast_fidelity", "twin_fidelity",
                                                    "participation_rate", "forecast_loss_oos"]].agg(["mean", "std"]).to_csv(st / "sweeps_summary.csv")
    write_report(run, df, sw, cmp, ni, fr, calib, fid_bins, abg, swp)
    print(f"report written to {run / 'REPORT.md'}")


if __name__ == "__main__":
    main()
