# FNDT Simulator (v2)

A network-level, closed-loop simulator and statistical evaluation pipeline for the
**Federated Network Digital Twin (FNDT)** framework for incentive-aware edge and
radio resource management in 5G/6G networks.

> **v2 replaces the earlier prototype.** In the old web demo, strategy outcomes were
> partly set by per-strategy constants. In v2, every strategy runs on the same
> environment and queueing model and differs only in the information it receives
> and the mechanism it uses. Nothing is tuned per strategy.

## What it models

- **Radio:** 7-site UMa layout with 3GPP TR 38.901 path loss and shadowing, the
  TR 36.942 attenuated Shannon bound, and load-coupled interference.
- **Traffic:** users with diurnal land-use traffic patterns, mobility, hotspots,
  and edge-compute workload.
- **Queues:** radio and MEC queues per site, using M/M/1 within a slot plus a
  Lindley-type backlog that carries overload between slots, with drops at the buffer limit.
- **Strategies:** the paper's seven — Static, Greedy, Centralized, FL-only, NDT-only,
  FNDT without incentive, and FNDT.
- **Learning:** FedAvg forecasting with the incentive engine
  R_i = αQ_i − βC_i + γP_i, where Q is validation gain, C is device energy and
  P is participation record.
- **Statistics:** 30 paired seeds, Wilcoxon signed-rank tests, Holm correction,
  bootstrap CIs, effect sizes, the paper's claim-safe labels, and sensitivity sweeps.

Full equations and sources: [`docs/v2/MODEL.md`](docs/v2/MODEL.md) and
[`docs/v2/REFERENCES.md`](docs/v2/REFERENCES.md).
Evaluation plan, committed before the confirmatory runs:
[`docs/v2/PREREGISTRATION.md`](docs/v2/PREREGISTRATION.md).
Development changes: [`docs/v2/DEVLOG.md`](docs/v2/DEVLOG.md).

## Reproduce

```bash
docker build --build-arg GIT_COMMIT=$(git rev-parse HEAD) -t fndt-sim:v2 .
docker run --rm -v "$PWD/results:/app/results" fndt-sim:v2 all      # tests + suite + sweeps + report
docker run --rm fndt-sim:v2 test                                     # 28 verification tests only
```

Outputs are written to `results/v2/`:

| Output | Contents |
|---|---|
| `REPORT.md` | Written statistical report |
| `stats/*.csv` | Every test with raw and Holm p-values, CIs and effect sizes |
| `figures/` | PNG at 300 dpi and vector PDF |
| `raw/*.csv` | One row per scenario × seed × strategy |
| `manifest.json` | Commit, package versions and seeds |

Without Docker (Python 3.12):

```bash
pip install -r requirements-v2.txt
PYTHONPATH=src python -m pytest tests_v2
PYTHONPATH=src python -m fndt.experiments all --out results/v2
PYTHONPATH=src python -m fndt.report --run results/v2
```

## Scope and limitations

The simulator works at network level. It does not implement a PHY/MAC stack and
uses synthetic traffic, so its results are controlled simulation evidence, not
deployment evidence.

See `docs/v2/MODEL.md` §9 for the full list.

---

## Legacy prototype (v1)

The original prototype remains in `src/fedndt_rrm`, `configs/*.yaml`, `scripts/`
and `web/` for reference.

# FedNDT-RRM Simulator

A deterministic, network-level simulator for evaluating a Federated Network Digital Twin (FedNDT) framework for incentive-aware Edge/RAN resource management.

Proposed research framing:

**A Generative AI-Assisted Federated Network Digital Twin Framework for Incentive-Aware Edge and Radio Resource Management in 5G/6G Networks.**

## Scope

This repository implements a lightweight research simulator for comparing resource-allocation strategies under controlled Edge/RAN stress scenarios.

It is designed for:

- research prototyping
- methodology development
- deterministic scenario evaluation
- paper-ready result generation
- future static web demo deployment

It does **not** claim to be a full physical-layer 5G/6G simulator.

## What the Simulator Does

The simulator includes:

1. synthetic Edge/RAN telemetry generation
2. local Network Digital Twin state construction
3. lightweight demand prediction
4. incentive/reliability scoring
5. static, greedy, and FedNDT-Incentive resource allocation
6. latency, SLA, throughput, fairness, prediction-error, overhead, and utility metrics
7. scenario-suite execution
8. paper-ready improvement analysis

## Compared Strategies

### Static

Allocates resources equally across Edge/RAN nodes.

This can produce high Jain resource fairness, but it does not adapt to demand imbalance, overloaded nodes, stale reporting, or mobility shifts.

### Greedy

Allocates resources based on observed demand.

In stress scenarios, delayed centralized observation can be used to model stale centralized awareness.

### FedNDT-Incentive

Uses local digital twin state, predicted demand, congestion risk, and incentive/reliability scores to allocate resources adaptively.

This is a proposed framework-level policy, not a proof of globally optimal network control.

## Quick Start

Install dependencies:

```bash
uv sync