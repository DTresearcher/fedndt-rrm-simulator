# Pre-registration of the confirmatory evaluation

Written and committed **before** any confirmatory seed (1000 and above) was run.
The git history shows the commit order. Model development and calibration used
seeds 0–4 only (see `DEVLOG.md`).

## Design

- **Strategies (7):** the paper's taxonomy. Two heuristic baselines (Static, Greedy) and five architectural designs (Centralized, FL-only, NDT-only, FNDT without incentive, FNDT). The mechanisms are defined in `MODEL.md` §5.
- **Scenarios (9):** baseline, high_load, hotspot, mobility, unreliable_telemetry, low_quality_contributors, high_noniid, heavy_dropout, radio_degradation (`configs/v2/scenarios/`).
- **Replication:** 30 independent seeds per scenario (1000–1029). Every strategy runs on the same environment realisation for a given seed (common random numbers), so all comparisons are paired.
- **Run length:** one simulated day of 1,440 one-minute control slots, after two warm-up days.

## Hypotheses and how each will be judged

These map onto the paper's claim-to-evidence binding.

| ID | Claim in the paper | Comparison | Evidence |
|---|---|---|---|
| H1 | FNDT improves latency/QoS over heuristic allocation | FNDT vs Static; FNDT vs Greedy | primary metrics |
| H2 | FNDT approaches centralized performance without centralizing raw data | FNDT vs Centralized | non-inferiority of mean latency (margin 5%), plus overhead and raw-record exposure |
| H3 | The twin adds value over FL alone | FNDT w/o incentive vs FL-only | primary metrics, twin fidelity |
| H4 | FL adds value over a non-learning twin | FNDT w/o incentive vs NDT-only | primary metrics, forecast fidelity |
| H5 | Federation avoids raw-data exposure | raw per-user records leaving sites | descriptive; deterministic by design |
| H6 | The incentive improves outcomes | FNDT vs FNDT w/o incentive | primary metrics, FL validation loss, participation rate, reward Jain index |
| H7 | Robustness across conditions | all of the above across the 9 scenarios, plus the sensitivity sweeps | label consistency, Friedman ranks |

**Primary metrics:** mean latency, p95 latency, SLA violation rate (requests over 100 ms, plus dropped traffic), drop rate.

**Secondary metrics:** p99 latency, throughput, Jain fairness of served/offered, forecast fidelity (1 − WAPE), twin fidelity (1 − NMAE of predicted vs realised mean latency, Eq. 1), FL validation loss, participation rate, control overhead.

## Analysis plan

1. **Effect measure.** For each seed, the direction-aware relative improvement of the focal strategy over the reference: (ref − focal)/ref if lower is better, (focal − ref)/ref if higher is better.
2. **Test.** Two-sided Wilcoxon signed-rank test on the 30 paired values.
3. **Multiplicity.** Holm correction within each scenario, applied separately to the family of primary tests (6 comparisons × 4 metrics = 24) and to the secondary family.
4. **Uncertainty.** 95% percentile-bootstrap CI of the mean per-seed improvement (10,000 resamples).
5. **Effect sizes.** Cohen's d_z and Vargha–Delaney A12.
6. **Claim-safe label.** Uses the paper's tiers (Fig. 3):
   - Strong: mean improvement ≥ 15%, p_Holm < 0.05 and CI excludes 0.
   - Modest: 5% to 15%, with the same significance conditions.
   - Regression: ≤ −5% with the same significance conditions.
   - Neutral: everything else.
7. **H2 test.** Non-inferiority holds when the lower bound of the 95% bootstrap CI of the improvement over Centralized is above −5%.
8. **Across strategies.** Friedman test and mean ranks per scenario (Demšar, 2006).

## Sensitivity analyses

These are the paper's stated next steps. Each uses 10 seeds (1000–1009).

| Axis | Values | Base scenario |
|---|---|---|
| Traffic pressure | 0.8–1.3 × load | baseline |
| Telemetry accuracy: report noise | 0.02, 0.1, 0.2, 0.3 | baseline |
| Telemetry accuracy: staleness | 0, 1, 2, 5 slots | baseline |
| Non-IID severity | 0, 0.25, 0.5, 0.75, 1.0 | baseline |
| Incentive weights (α, β, γ) | simplex grid, step 0.25 | baseline and low_quality_contributors |
| Participation elasticity | 0, 0.3, 0.6 | heavy_dropout |

## Reporting commitments

- Every result is reported, including Neutral and Regression outcomes, and including comparisons where a baseline wins.
- No scenario, seed, metric or strategy will be dropped after the confirmatory run.
- Any change to the model after this point must be reported as a deviation, and all confirmatory results re-run.
