"""Build the static results website (GitHub Pages) from a finished results directory.

The site only displays outputs of the reproducible pipeline; it runs no simulation.
Usage: python -m fndt.site --results results --out site
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

import pandas as pd

from fndt.simulator import STRATEGIES
from fndt.stats import COMPARISONS

LABEL = {s.name: s.label for s in STRATEGIES}
ORDER = [s.name for s in STRATEGIES]
PAIRS = [(f, r) for f, r, _ in COMPARISONS]
TAG = {"Strong improvement": "strong", "Modest improvement": "modest", "Neutral": "neutral", "Regression": "regression"}

CSS = """
:root{--bg:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--muted:#52514e;--line:#e4e3df;--accent:#2a78d6;
--strong:#0f6e2e;--modest:#2e8b57;--neutral:#6b6a66;--regression:#c0392b;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--panel:#1d1d1b;--ink:#f0efec;--muted:#b9b8b0;--line:#33322f;
--accent:#3987e5;--strong:#4caf6e;--modest:#7cc48f;--neutral:#a3a29b;--regression:#e66767;color-scheme:dark}
img.fig{background:#fff;border-radius:6px}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:32px 16px 64px}h1{font-size:28px;margin:0 0 4px}h2{font-size:20px;margin:40px 0 10px;border-top:1px solid var(--line);padding-top:24px}
h3{font-size:16px;margin:22px 0 8px}p,li{color:var(--ink)}.muted{color:var(--muted)}a{color:var(--accent)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:12px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600}.scroll{overflow-x:auto}
.strong{color:var(--strong);font-weight:600}.modest{color:var(--modest);font-weight:600}.neutral{color:var(--neutral)}.regression{color:var(--regression);font-weight:600}
img.fig{width:100%;height:auto;border:1px solid var(--line)}code{font-size:13px}
"""


def _cell(row) -> str:
    cls = TAG[row.label]
    return f'{row.improvement_pct:+.1f}% <span class="{cls}">{html.escape(row.label.replace(" improvement", ""))}</span>'


def build(results: Path, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    (out / "figures").mkdir(parents=True)
    for f in (results / "figures").glob("*"):
        shutil.copy(f, out / "figures" / f.name)
    (out / "data").mkdir()
    for f in list((results / "stats").glob("*.csv")) + [results / "manifest.json", results / "REPORT.md"]:
        shutil.copy(f, out / "data" / f.name)

    man = json.loads((results / "manifest.json").read_text())
    cmp = pd.read_csv(results / "stats" / "comparisons.csv")
    ni = pd.read_csv(results / "stats" / "non_inferiority.csv")
    raw = pd.read_csv(results / "raw" / "main.csv")
    scen = list(dict.fromkeys(raw.scenario))
    desc = raw.groupby(["scenario", "strategy"]).mean(numeric_only=True)

    m = cmp[cmp.metric == "mean_latency_ms"]
    rows = []
    for sc in scen:
        cells = []
        for f, r in PAIRS:
            x = m[(m.scenario == sc) & (m.focal == f) & (m.reference == r)]
            cells.append(_cell(x.iloc[0]) if len(x) else "–")
        rows.append(f"<tr><td>{sc.replace('_', ' ')}</td><td>{desc.loc[(sc, 'fndt'), 'mean_latency_ms']:.1f}</td><td>" + "</td><td>".join(cells) + "</td></tr>")
    head = "".join(f"<th>{LABEL[f]} vs {LABEL[r]}</th>" for f, r in PAIRS)
    main_table = f'<div class="scroll"><table><tr><th>Scenario</th><th>FNDT mean latency (ms)</th>{head}</tr>{"".join(rows)}</table></div>'

    base = desc.xs("baseline")
    ov_rows = "".join(
        f"<tr><td>{LABEL[k]}</td><td>{base.loc[k, 'mean_latency_ms']:.1f}</td><td>{base.loc[k, 'sla_violation_rate']:.3f}</td>"
        f"<td>{base.loc[k, 'overhead_mb']:.3f}</td><td>{base.loc[k, 'raw_records_exposed']:,.0f}</td></tr>" for k in ORDER)
    ni_rows = "".join(
        f"<tr><td>{r.scenario.replace('_', ' ')}</td><td>{r.improvement_pct:+.2f}%</td><td>[{r.ci_low:+.2f}, {r.ci_high:+.2f}]</td>"
        f"<td class='{'strong' if r.non_inferior else 'regression'}'>{'yes' if r.non_inferior else 'no'}</td></tr>" for r in ni.itertuples())

    def fig(name, caption):
        return f'<figure class="card"><img class="fig" src="figures/{name}.png" alt="{html.escape(caption)}" loading="lazy"><figcaption class="muted">{html.escape(caption)} · <a href="figures/{name}.pdf">vector PDF</a></figcaption></figure>'

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FNDT Simulator Results</title><style>{CSS}</style></head><body><main>
<h1>FNDT Simulator — Results</h1>
<p class="muted">Federated Network Digital Twin for incentive-aware edge and radio resource management · results of commit <code>{html.escape(man['git_commit'][:10])}</code>,
Python {html.escape(man['python'])}, seeds {man['confirmatory_seeds'][0]}–{man['confirmatory_seeds'][1]}. This page shows outputs of the reproducible Docker pipeline only; no simulation runs in the browser.</p>
<div class="card"><b>How to read this.</b> The paper's seven strategies (Static, Greedy, Centralized, FL-only, NDT-only, FNDT without incentive, FNDT)
and two diagnostic baselines (Greedy-SR: a non-learning heuristic that uses channel quality; FL + state: federated forecasts and network state without the twin's what-if search)
are evaluated on the same network model, {len(set(raw.scenario))} scenarios and 30 paired seeds. Each effect is the relative difference of means with a paired
bootstrap 95% CI, tested with a two-sided Wilcoxon signed-rank test and Holm correction.
Labels use pre-registered claim-safe tiers: <span class="strong">Strong</span> (≥15%), <span class="modest">Modest</span> (5–15%),
<span class="neutral">Neutral</span> (&lt;5% or not significant), <span class="regression">Regression</span> (≤−5%). Positive percentages mean the first-named strategy is better.</div>

<h2>Main comparison: mean latency</h2>{main_table}
{fig('labels_mean_latency_ms', 'Claim-safe labels for mean latency across scenarios')}
{fig('forest_mean_latency_ms', 'Paired differences with 95% bootstrap CIs; shaded band is the ±5% Neutral zone')}
{fig('scenarios_mean_latency_ms', 'Mean latency by scenario: mean and 95% CI over 30 seeds')}

<h2>Performance, overhead and raw-data exposure (baseline)</h2>
<div class="scroll"><table><tr><th>Strategy</th><th>Mean latency (ms)</th><th>SLA violation rate</th><th>Control overhead (MB/day)</th><th>Raw user records leaving sites per day</th></tr>{ov_rows}</table></div>
<h3>Non-inferiority of FNDT to Centralized (mean latency, 5% margin)</h3>
<div class="scroll"><table><tr><th>Scenario</th><th>Improvement</th><th>95% CI</th><th>Non-inferior</th></tr>{ni_rows}</table></div>
{fig('tradeoff_baseline', 'Mean latency against control-plane overhead, baseline scenario')}

<h2>Fidelity</h2><div class="grid">{fig('scenarios_twin_fidelity', 'Twin fidelity: 1 − normalised error of predicted vs realised latency')}{fig('scenarios_forecast_fidelity', 'Forecast fidelity: 1 − WAPE of load forecasts')}
{fig('sweep_service_variability_twin_fidelity', 'Twin fidelity when true service times deviate from the twin model')}</div>

<h2>Sensitivity analyses</h2><div class="grid">
{fig('sweep_traffic_pressure_mean_latency_ms', 'Traffic pressure')}{fig('sweep_report_noise_mean_latency_ms', 'Telemetry report noise')}
{fig('sweep_telemetry_staleness_mean_latency_ms', 'Telemetry staleness')}{fig('sweep_noniid_mean_latency_ms', 'Non-IID severity')}
{fig('sweep_service_variability_mean_latency_ms', 'Service-time variability (twin model error)')}{fig('sweep_elasticity_participation_rate', 'Participation elasticity')}
{fig('abg_baseline', 'Incentive weights α, β, γ: baseline')}{fig('abg_low_quality_contributors', 'Incentive weights α, β, γ: low-quality contributors')}</div>

<h2>Data and reproduction</h2>
<ul><li>Every statistical test: <a href="data/comparisons.csv">comparisons.csv</a>; descriptive statistics: <a href="data/descriptive.csv">descriptive.csv</a>; full written report: <a href="data/REPORT.md">REPORT.md</a>; provenance: <a href="data/manifest.json">manifest.json</a>.</li>
<li>Reproduce: <code>docker build -t fndt-sim . &amp;&amp; docker run --rm -v "$PWD/results:/app/results" fndt-sim all</code></li>
<li>Model specification, pre-registration, development log and references are in the repository's <code>docs/</code> folder.</li></ul>
<p class="muted">Scope: network-level simulation with synthetic traffic; results are controlled simulation evidence, not deployment evidence.</p>
</main></body></html>"""
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / ".nojekyll").write_text("")
    print(f"site written to {out}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="site")
    a = ap.parse_args(argv)
    build(Path(a.results), Path(a.out))


if __name__ == "__main__":
    main()
