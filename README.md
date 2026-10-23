# FNDT Simulator

A network-level, closed-loop simulator and statistical evaluation pipeline for the
**Federated Network Digital Twin (FNDT)** framework for incentive-aware edge and radio
resource management in 5G/6G networks.

It evaluates the paper's strategy taxonomy plus two diagnostic baselines, all on one
shared network and queueing model:

- **Heuristics:** Static, Greedy.
- **Architectural designs:** Centralized, FL-only, NDT-only, FNDT without incentive, FNDT.
- **Diagnostic baselines:** Greedy-SR, FL + state.

Strategies differ only in the information they receive and the mechanism they use.
No strategy receives a performance factor.

## What is modelled

| Part | Model | Sources |
|---|---|---|
| Radio | 7-site UMa layout, path loss and shadowing; attenuated Shannon bound; load-coupled interference | 3GPP TR 38.901, TR 36.942, ITU-R M.2412 |
| Traffic | Land-use diurnal profiles, mobility, hotspots, edge-compute workload | Xu et al. 2017, Mao et al. 2017 |
| Queues | Radio and MEC queue per site: M/M/1 (or M/G/1) within a slot plus a Lindley-type backlog with buffer drops | Kleinrock 1975, Lindley 1952 |
| Allocation | Kleinrock square-root assignment; twin what-if over candidate allocations | Kleinrock 1976 |
| Information | One explicit channel for every message to the controller: aggregation noise, pipeline faults, stale repeats, delay | docs/MODEL.md §5 |
| Learning | FedAvg forecasting; incentive engine R_i = αQ_i − βC_i + γP_i (quality = validation gain, cost = device energy, participation record) | McMahan et al. 2017, Cao et al. 2021, Yang et al. 2021, Kang et al. 2019 |
| Statistics | 30 paired seeds; Wilcoxon signed-rank with Holm correction; paired bootstrap CIs; d_z and A12; claim-safe labels; non-inferiority; Friedman ranks | Wilcoxon 1945, Holm 1979, Efron & Tibshirani 1993, Vargha & Delaney 2000, Demšar 2006, Arcuri & Briand 2011 |

## Documentation

| File | Contents |
|---|---|
| [`docs/MODEL.md`](docs/MODEL.md) | Equations, information model, strategies, metrics and limitations |
| [`docs/REFERENCES.md`](docs/REFERENCES.md) | Every source in APA 7, with verified DOIs |
| [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md) | Evaluation plan, committed before any confirmatory run |
| [`docs/PREREGISTRATION_AMENDMENT_1.md`](docs/PREREGISTRATION_AMENDMENT_1.md) | Amendment after the internal audit, committed before the reported runs |
| [`docs/DEVLOG.md`](docs/DEVLOG.md) | Every development change, with its reason |

## Results

| Path | Contents |
|---|---|
| `results/REPORT.md` | Full statistical report |
| `results/stats/` | Every test, with raw and Holm p-values, CIs and effect sizes |
| `results/figures/` | 300 dpi PNG and vector PDF |
| `results/raw/` | One row per scenario × seed × strategy |
| `results/manifest.json` | Commit, package versions and seeds |

The same results are published as a static page via GitHub Pages. That page runs no
simulation; it only displays these files.

## Reproduce

```bash
docker build --build-arg GIT_COMMIT=$(git rev-parse HEAD) -t fndt-sim .
docker run --rm -v "$PWD/results:/app/results" fndt-sim all    # tests, suite, sweeps, report, site
docker run --rm fndt-sim test                                  # verification tests only
```

A full run takes about 30–40 minutes on 8 cores. Results are deterministic for a given
commit and seed list.

Without Docker (Python 3.12):

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m pytest tests
PYTHONPATH=src python -m fndt.experiments all --out results
PYTHONPATH=src python -m fndt.report --run results
```

## Scope

This is a network-level abstraction with synthetic traffic. It does not implement a
PHY/MAC stack and is not validated against operator data. See `docs/MODEL.md` §11.

## Repository layout

```
src/fndt/           simulator, experiments, statistics, report and site generators
configs/scenarios/  scenario definitions (YAML)
tests/              verification and integrity tests
docs/               model specification, plan, amendment, development log, references
results/            committed outputs of the reported run
legacy/             archived first prototype and web demo (not used for any reported result)
```
