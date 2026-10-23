"""Experiment runner: confirmatory scenario suite and pre-registered sensitivity sweeps.

Usage:
    python -m fndt.experiments all --out results --workers 8
    python -m fndt.experiments main --seeds 30
    python -m fndt.experiments sweeps --sweep-seeds 20
Development used seeds 0-4 only. The confirmatory runs reported in results/ use
seeds starting at 2000 (Amendment 1); seeds 1000-1029 were used by the superseded first run.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from fndt.config import load_scenario
from fndt.environment import build_environment
from fndt.simulator import STRATEGIES, STRATEGY_BY_NAME, Run, _site_aggregates

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = ROOT / "configs" / "scenarios"
MAIN_SCENARIOS = [
    "baseline",
    "high_load",
    "hotspot",
    "mobility",
    "unreliable_telemetry",
    "low_quality_contributors",
    "corrupted_measurements",
    "high_noniid",
    "heavy_dropout",
    "radio_degradation",
    "model_mismatch",
]
CONFIRMATORY_SEED0 = 2000
ALL = [s.name for s in STRATEGIES]


def _simplex(step: float):
    k = int(round(1 / step))
    for a in range(k + 1):
        for b in range(k + 1 - a):
            yield round(a * step, 4), round(b * step, 4), round(1 - (a + b) * step, 4)


def sweep_jobs(seeds: list[int]):
    """Sensitivity axes: the paper's stated next steps plus twin model error."""
    jobs = []
    for v in (0.8, 0.9, 1.0, 1.1, 1.2, 1.3):
        jobs.append(("traffic_pressure", v, "baseline", {"traffic": {"load_scale": v}}, ALL))
    for v in (0.02, 0.1, 0.2, 0.3):
        jobs.append(("report_noise", v, "baseline", {"telemetry": {"report_noise": v}}, ALL))
    for v in (0, 1, 2, 5):
        jobs.append(("telemetry_staleness", v, "baseline", {"telemetry": {"staleness_slots": v}}, ALL))
    for v in (0.0, 0.25, 0.5, 0.75, 1.0):
        jobs.append(("noniid", v, "baseline", {"traffic": {"noniid": v}}, ALL))
    for v in (0.5, 1.0, 2.0, 3.0):
        jobs.append(("service_variability", v, "baseline", {"network": {"service_scv": v}}, ALL))
    for v in (0.0, 0.3, 0.6):
        jobs.append(("elasticity", v, "heavy_dropout", {"incentive": {"elasticity": v}}, ["fndt_no_incentive", "fndt"]))
    grid = list(_simplex(0.25)) + [(0.5, 0.2, 0.3)]  # simplex grid plus the default weights
    for base in ("baseline", "low_quality_contributors"):
        for a, b, g in grid:
            jobs.append((f"alpha_beta_gamma:{base}", f"{a}/{b}/{g}", base,
                         {"incentive": {"alpha": a, "beta": b, "gamma": g}}, ["fndt_no_incentive", "fndt"]))
    return [(axis, value, base, extra, strategies, seed) for axis, value, base, extra, strategies in jobs for seed in seeds]


def _work(job) -> list[dict]:
    axis, value, scenario_name, extra, strategies, seed = job
    scenario = load_scenario(SCENARIO_DIR / f"{scenario_name}.yaml", extra)
    env = build_environment(scenario, seed)
    shared = _site_aggregates(env)
    rows = []
    for name in strategies:
        t0 = time.perf_counter()
        res = Run(env, STRATEGY_BY_NAME[name], shared).run()
        rows.append({"axis": axis, "value": value, "scenario": scenario_name, "seed": seed, "strategy": name,
                     "config_digest": scenario.digest(), "runtime_s": time.perf_counter() - t0,
                     **{k: float(v) for k, v in res.items()}})
    return rows


def _run_jobs(jobs, workers: int, label: str) -> pd.DataFrame:
    rows = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, out in enumerate(pool.map(_work, jobs, chunksize=1), 1):
            rows.extend(out)
            if i % max(1, len(jobs) // 20) == 0 or i == len(jobs):
                print(f"[{label}] {i}/{len(jobs)} environments, {time.time() - t0:.0f}s", flush=True)
    return pd.DataFrame(rows)


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unavailable"


def manifest(out: Path, args) -> None:
    import matplotlib
    import scipy
    import yaml

    info = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": " ".join(sys.argv),
        "git_commit": os.environ.get("GIT_COMMIT") or _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")) if _git("rev-parse", "HEAD") != "unavailable" else "unknown",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {"numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
                     "matplotlib": matplotlib.__version__, "pyyaml": yaml.__version__},
        "confirmatory_seeds": [args.seed0, args.seed0 + args.seeds - 1],
        "sweep_seeds": [args.seed0, args.seed0 + args.sweep_seeds - 1],
        "scenarios": {n: load_scenario(SCENARIO_DIR / f"{n}.yaml").digest() for n in MAIN_SCENARIOS},
    }
    (out / "manifest.json").write_text(json.dumps(info, indent=2))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["main", "sweeps", "all"])
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--sweep-seeds", type=int, default=20)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--seed0", type=int, default=CONFIRMATORY_SEED0, help="first seed; use 0 for development checks")
    args = ap.parse_args(argv)
    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    manifest(out, args)
    if args.what in ("main", "all"):
        seeds = list(range(args.seed0, args.seed0 + args.seeds))
        jobs = [("main", "", s, None, ALL, seed) for s in MAIN_SCENARIOS for seed in seeds]
        _run_jobs(jobs, args.workers, "main").to_csv(out / "raw" / "main.csv", index=False)
    if args.what in ("sweeps", "all"):
        seeds = list(range(args.seed0, args.seed0 + args.sweep_seeds))
        _run_jobs(sweep_jobs(seeds), args.workers, "sweeps").to_csv(out / "raw" / "sweeps.csv", index=False)


if __name__ == "__main__":
    main()
