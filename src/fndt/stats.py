"""Statistical analysis for paired simulation experiments.

Seeds are paired across strategies (common random numbers), so comparisons use
paired tests: two-sided Wilcoxon signed-rank (Wilcoxon, 1945), Holm correction
within each scenario's family of primary tests (Holm, 1979), percentile
bootstrap confidence intervals (Efron & Tibshirani, 1993), Cohen's d_z and the
Vargha-Delaney A12 effect size (Vargha & Delaney, 2000), and the Friedman test
with mean ranks across all strategies (Demsar, 2006). The procedure follows
Arcuri & Briand (2011) for randomised algorithms.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

LOWER_IS_BETTER = {
    "mean_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "sla_violation_rate",
    "drop_rate",
    "overhead_mb",
    "raw_records_exposed",
    "fl_energy_j",
    "fl_final_loss",
    "fl_rounds_to_converge",
    "reward_cv",
}
PRIMARY_METRICS = ["mean_latency_ms", "p95_latency_ms", "sla_violation_rate", "drop_rate"]
SECONDARY_METRICS = [
    "p99_latency_ms",
    "throughput_mbps",
    "jain_satisfaction",
    "forecast_fidelity",
    "twin_fidelity",
    "fl_final_loss",
    "participation_rate",
    "overhead_mb",
]

# Pre-registered comparisons (docs/v2/PREREGISTRATION.md): (focal, reference, hypothesis)
COMPARISONS = [
    ("fndt", "static", "H1 latency vs heuristic"),
    ("fndt", "greedy", "H1 latency vs heuristic"),
    ("fndt", "centralized", "H2 near-centralized performance"),
    ("fndt_no_incentive", "fl_only", "H3 value of the twin"),
    ("fndt_no_incentive", "ndt_only", "H4 value of federated learning"),
    ("fndt", "fndt_no_incentive", "H6 value of the incentive"),
]

STRONG, MODEST, NEUTRAL_BAND = 15.0, 5.0, 5.0
ALPHA = 0.05


def improvement_pct(focal: np.ndarray, ref: np.ndarray, metric: str) -> np.ndarray:
    """Per-seed direction-aware relative improvement of focal over its paired ref, in percent.

    Lower-is-better: (ref - focal) / ref; higher-is-better: (focal - ref) / ref (positive = better).
    """
    denom = np.maximum(np.abs(ref), 1e-12)
    diff = (ref - focal) if metric in LOWER_IS_BETTER else (focal - ref)
    return 100.0 * diff / denom


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
    if n < 3:
        return {"n": n}
    per_seed = improvement_pct(focal, ref, metric)
    d = per_seed  # paired differences in percent of the reference mean
    if np.allclose(d, 0):
        p = 1.0
    else:
        p = float(stats.wilcoxon(focal, ref, zero_method="wilcox").pvalue)
    sd = d.std(ddof=1)
    dz = float(d.mean() / sd) if sd > 0 else 0.0
    lo, hi = bootstrap_ci(d, seed=seed)
    sign = -1 if metric in LOWER_IS_BETTER else 1
    a12 = vargha_delaney_a12(sign * focal, sign * ref)
    return {
        "n": n,
        "focal_mean": float(focal.mean()),
        "focal_sd": float(focal.std(ddof=1)),
        "ref_mean": float(ref.mean()),
        "ref_sd": float(ref.std(ddof=1)),
        "improvement_pct": float(d.mean()),
        "ci_low": lo,
        "ci_high": hi,
        "p_raw": p,
        "cohen_dz": dz,
        "a12": a12,
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


def claim_label(impr: float, p_adj: float, ci_low: float, ci_high: float) -> str:
    """Claim-safe label of the paper (Fig. 3) with a significance requirement."""
    significant = p_adj < ALPHA and (ci_low > 0 or ci_high < 0)
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
            r["label"] = claim_label(r["improvement_pct"], r["p_holm"], r["ci_low"], r["ci_high"])
        rows.extend(family)
    cols = ["scenario", "hypothesis", "focal", "reference", "metric", "primary", "n", "focal_mean", "focal_sd",
            "ref_mean", "ref_sd", "improvement_pct", "ci_low", "ci_high", "p_raw", "p_holm", "cohen_dz", "a12", "label"]
    return pd.DataFrame(rows)[cols]


def non_inferiority(df: pd.DataFrame, focal="fndt", ref="centralized", metric="mean_latency_ms", margin=MODEST) -> pd.DataFrame:
    """H2: focal is non-inferior to ref if the lower 95% CI bound of the improvement exceeds -margin percent."""
    rows = []
    for scenario, block in df.groupby("scenario", sort=False):
        w = block.pivot(index="seed", columns="strategy", values=metric)
        d = improvement_pct(w[focal].to_numpy(), w[ref].to_numpy(), metric)
        lo, hi = bootstrap_ci(d, seed=7)
        rows.append({"scenario": scenario, "metric": metric, "improvement_pct": d.mean(), "ci_low": lo,
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
