"""Statistical analysis for paired simulation experiments.

Seeds are paired across strategies (common random numbers), so comparisons use
paired tests: two-sided Wilcoxon signed-rank (Wilcoxon, 1945), Holm correction
within each scenario's family of primary tests (Holm, 1979; a global family is
reported as a sensitivity check), the relative difference of means with a paired
percentile bootstrap CI (Efron & Tibshirani, 1993), Cohen's d_z and the
Vargha-Delaney A12 effect size (Vargha & Delaney, 2000), and the Friedman test
with mean ranks across all strategies (Demsar, 2006). The procedure follows
Arcuri & Briand (2011) for randomised algorithms.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

RATE_METRICS = {"sla_violation_rate", "drop_rate"}
MIN_RATE_DIFF = 0.001  # 0.1 percentage point: smaller absolute differences are labelled Neutral
LOWER_IS_BETTER = {
    "mean_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "sla_violation_rate",
    "drop_rate",
    "overhead_mb",
    "raw_records_exposed",
    "fl_energy_j",
    "forecast_loss_oos",
    "fl_rounds_to_converge",
    "reward_cv",
}
PRIMARY_METRICS = ["mean_latency_ms", "p95_latency_ms", "sla_violation_rate", "drop_rate"]
SECONDARY_METRICS = [
    "p99_latency_ms",
    "throughput_mbps",
    "fl_energy_j",
    "forecast_fidelity",
    "twin_fidelity",
    "forecast_loss_oos",
    "participation_rate",
    "overhead_mb",
]

# Comparisons (docs/PREREGISTRATION.md and Amendment 1): (focal, reference, hypothesis)
COMPARISONS = [
    ("fndt", "static", "H1 vs heuristics"),
    ("fndt", "greedy", "H1 vs heuristics"),
    ("fndt", "greedy_sr", "H1 vs heuristics"),
    ("fndt", "centralized", "H2 vs centralized"),
    ("fndt_no_incentive", "fl_only", "H3 value of the twin"),
    ("fndt_no_incentive", "fl_state", "H3b value of the what-if search"),
    ("fndt_no_incentive", "ndt_only", "H4 value of federated learning"),
    ("fndt", "fndt_no_incentive", "H6 value of the incentive"),
]

STRONG, MODEST, NEUTRAL_BAND = 15.0, 5.0, 5.0
ALPHA = 0.05


def improvement_pct(focal: np.ndarray, ref: np.ndarray, metric: str) -> np.ndarray:
    """Per-seed direction-aware relative improvement (mean-of-ratios; sensitivity analysis only)."""
    denom = np.maximum(np.abs(ref), 1e-12)
    diff = (ref - focal) if metric in LOWER_IS_BETTER else (focal - ref)
    return 100.0 * diff / denom


def ratio_of_means(focal: np.ndarray, ref: np.ndarray, metric: str) -> float:
    """Direction-aware relative improvement of the mean (positive = focal better), in percent."""
    denom = abs(ref.mean())
    if denom < 1e-12:
        return float("nan")
    diff = (ref.mean() - focal.mean()) if metric in LOWER_IS_BETTER else (focal.mean() - ref.mean())
    return 100.0 * diff / denom


def paired_bootstrap_ratio(focal, ref, metric, n_boot=10_000, seed=0, level=0.95):
    """Percentile bootstrap CI of ratio_of_means, resampling seeds as pairs."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(focal), (n_boot, len(focal)))
    fm, rm = focal[idx].mean(axis=1), ref[idx].mean(axis=1)
    denom = np.maximum(np.abs(rm), 1e-12)
    vals = 100.0 * ((rm - fm) if metric in LOWER_IS_BETTER else (fm - rm)) / denom
    lo, hi = np.percentile(vals, [100 * (1 - level) / 2, 100 * (1 + level) / 2])
    return float(lo), float(hi)


def bootstrap_ci(values: np.ndarray, n_boot: int = 10_000, seed: int = 0, level: float = 0.95):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), (n_boot, len(values)))
    means = values[idx].mean(axis=1)
    lo, hi = np.percentile(means, [100 * (1 - level) / 2, 100 * (1 + level) / 2])
    return float(lo), float(hi)


def vargha_delaney_a12(x: np.ndarray, y: np.ndarray) -> float:
    """Probability that a draw from x is better than a draw from y (ties count half), for 'higher is better'."""
    gt = (x[:, None] > y[None, :]).sum()
    eq = (x[:, None] == y[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(x) * len(y)))


def paired_test(focal: np.ndarray, ref: np.ndarray, metric: str, seed: int = 0) -> dict:
    ok = np.isfinite(focal) & np.isfinite(ref)
    focal, ref = focal[ok], ref[ok]
    n = len(focal)
    if n < 3 or abs(ref.mean()) < 1e-12:
        return {"n": 0}
    d = focal - ref
    p = 1.0 if np.allclose(d, 0) else float(stats.wilcoxon(focal, ref, zero_method="wilcox").pvalue)
    sd = d.std(ddof=1)
    sign = -1 if metric in LOWER_IS_BETTER else 1
    lo, hi = paired_bootstrap_ratio(focal, ref, metric, seed=seed)
    mor = improvement_pct(focal, ref, metric)
    return {
        "n": n,
        "focal_mean": float(focal.mean()),
        "focal_sd": float(focal.std(ddof=1)),
        "ref_mean": float(ref.mean()),
        "ref_sd": float(ref.std(ddof=1)),
        "improvement_pct": ratio_of_means(focal, ref, metric),
        "ci_low": lo,
        "ci_high": hi,
        "abs_diff": float(d.mean()),  # focal minus reference, in metric units
        "improvement_pct_mean_of_ratios": float(mor.mean()),
        "p_raw": p,
        "cohen_dz": float(sign * d.mean() / sd) if sd > 0 else 0.0,
        "a12": vargha_delaney_a12(sign * focal, sign * ref),
    }


def holm(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = np.argsort(pvalues)
    adjusted = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted.tolist()


def claim_label(impr: float, p_adj: float, ci_low: float, ci_high: float, metric: str = "", abs_diff: float = np.inf) -> str:
    """Claim-safe label of the paper (Fig. 3) with a significance requirement.

    Rate metrics additionally need an absolute difference of at least MIN_RATE_DIFF.
    """
    significant = p_adj < ALPHA and (ci_low > 0 or ci_high < 0)
    if metric in RATE_METRICS and abs(abs_diff) < MIN_RATE_DIFF:
        significant = False
    if significant and impr >= STRONG:
        return "Strong improvement"
    if significant and impr >= MODEST:
        return "Modest improvement"
    if significant and impr <= -MODEST:
        return "Regression"
    return "Neutral"


def compare(df: pd.DataFrame, comparisons=COMPARISONS, metrics=None) -> pd.DataFrame:
    """All pre-registered comparisons for every scenario. df: one row per (scenario, seed, strategy)."""
    metrics = metrics or PRIMARY_METRICS + SECONDARY_METRICS
    rows = []
    for scenario, block in df.groupby("scenario", sort=False):
        wide = {m: block.pivot(index="seed", columns="strategy", values=m) for m in metrics}
        family = []
        for focal, ref, hyp in comparisons:
            for metric in metrics:
                w = wide[metric]
                if focal not in w or ref not in w:
                    continue
                res = paired_test(w[focal].to_numpy(float), w[ref].to_numpy(float), metric, seed=len(rows))
                if res.get("n", 0) < 3:
                    continue
                res.update(scenario=scenario, focal=focal, reference=ref, hypothesis=hyp, metric=metric,
                           primary=metric in PRIMARY_METRICS)
                family.append(res)
        primary = [r for r in family if r["primary"]]
        for r, p in zip(primary, holm([r["p_raw"] for r in primary])):
            r["p_holm"] = p
        secondary = [r for r in family if not r["primary"]]
        for r, p in zip(secondary, holm([r["p_raw"] for r in secondary])):
            r["p_holm"] = p
        for r in family:
            r["label"] = claim_label(r["improvement_pct"], r["p_holm"], r["ci_low"], r["ci_high"], r["metric"], r["abs_diff"])
        rows.extend(family)
    out = pd.DataFrame(rows)
    # Sensitivity: one global Holm family over every primary test of every scenario.
    prim = out.primary
    out.loc[prim, "p_holm_global"] = holm(out.loc[prim, "p_raw"].tolist())
    out["label_global_holm"] = [
        claim_label(r.improvement_pct, r.p_holm_global, r.ci_low, r.ci_high, r.metric, r.abs_diff) if r.primary else ""
        for r in out.itertuples()
    ]
    cols = ["scenario", "hypothesis", "focal", "reference", "metric", "primary", "n", "focal_mean", "focal_sd",
            "ref_mean", "ref_sd", "improvement_pct", "ci_low", "ci_high", "abs_diff", "improvement_pct_mean_of_ratios",
            "p_raw", "p_holm", "p_holm_global", "cohen_dz", "a12", "label", "label_global_holm"]
    return out[cols]


def non_inferiority(df: pd.DataFrame, focal="fndt", ref="centralized", metric="mean_latency_ms", margin=MODEST) -> pd.DataFrame:
    """H2: focal is non-inferior to ref if the lower 95% CI bound of the improvement exceeds -margin percent."""
    rows = []
    for scenario, block in df.groupby("scenario", sort=False):
        w = block.pivot(index="seed", columns="strategy", values=metric)
        f, r = w[focal].to_numpy(float), w[ref].to_numpy(float)
        lo, hi = paired_bootstrap_ratio(f, r, metric, seed=7)
        rows.append({"scenario": scenario, "metric": metric, "improvement_pct": ratio_of_means(f, r, metric), "ci_low": lo,
                     "ci_high": hi, "margin_pct": margin, "non_inferior": lo > -margin})
    return pd.DataFrame(rows)


def friedman_ranks(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = []
    for scenario, block in df.groupby("scenario", sort=False):
        w = block.pivot(index="seed", columns="strategy", values=metric).dropna(axis=1)
        sign = 1 if metric in LOWER_IS_BETTER else -1
        ranks = (sign * w).rank(axis=1).mean()
        p = float(stats.friedmanchisquare(*[w[c] for c in w.columns]).pvalue)
        rows.append({"scenario": scenario, "metric": metric, "friedman_p": p, **{f"rank_{k}": v for k, v in ranks.items()}})
    return pd.DataFrame(rows)


def describe(df: pd.DataFrame, metrics) -> pd.DataFrame:
    """Mean, SD and 95% t-interval per scenario and strategy."""
    out = []
    for (scenario, strategy), g in df.groupby(["scenario", "strategy"], sort=False):
        row = {"scenario": scenario, "strategy": strategy}
        for m in metrics:
            x = g[m].to_numpy(float)
            x = x[np.isfinite(x)]
            if len(x) < 2:
                continue
            half = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
            row[f"{m}_mean"], row[f"{m}_sd"], row[f"{m}_ci95"] = x.mean(), x.std(ddof=1), half
        out.append(row)
    return pd.DataFrame(out)
