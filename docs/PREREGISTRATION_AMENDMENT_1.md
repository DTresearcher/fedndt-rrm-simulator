# Amendment 1 to the evaluation plan

This amendment is committed **before** the confirmatory runs it governs (seeds 2000–2029; sweep seeds 2000–2019). The git history records the order.

It supersedes the first confirmatory run (seeds 1000–1029). That run is not reported as evidence, because an internal audit found the defects listed below. Its outputs are kept outside the repository for transparency on request.

## Why the plan was amended

Two independent internal reviews ran after the first confirmatory run:
- a code audit checking correctness, information leakage and fairness between strategies;
- a methodological critique written from a reviewer's perspective.

They found defects that changed reported conclusions:

| Finding | Effect in the first run |
|---|---|
| FL strategies bypassed the report channel: no reporting noise, no stale messages | Inflated FNDT's advantage under unreliable telemetry |
| Low-quality sites' noise corrupted FL inference inputs, not only training data | Produced artificial regressions for every FL-based arm |
| Centralized received site-level reports instead of raw telemetry, while being charged for raw telemetry | Handicapped the upper-bound baseline |
| Twin state (channel quality, backlog) bypassed the report channel | Gave twin strategies cleaner information than intended |
| MEC buffer drops were computed but not counted | Flattered Static |
| Training used fresher data than inference under staleness | Inconsistent information timing |
| FL model loss was measured in-sample | Overstated model quality |
| Report noise was biased upward (not mean-corrected) | Biased every report-based strategy |
| Users could drift out of the simulated area under mobility | Turned the mobility scenario into a coverage collapse |
| Relative labels on near-zero rates were unstable | Meaningless labels on drop rates |

Each fix and its reason is recorded in `DEVLOG.md` (Amendment 1 section). All fixes were developed and checked on seeds 0–4 only.

## Changes to the design

1. **One information model.** Each site measures its own load (measurement noise). Every message to the controller passes the same channel: aggregation noise, pipeline faults, stale repeats and delay. This covers load reports, FL forecasts and twin state alike. Raw per-user telemetry (Centralized) avoids aggregation noise only. Training logs can be noisier than live counters.
2. **Two diagnostic arms** separate the contributions of each component:
   - **Greedy-SR:** last report, reported channel quality, square-root allocation, no learning. This tests whether gains come from learning or from the allocation rule.
   - **FL + state:** federated forecasts plus reported state, single square-root allocation, no what-if search. This separates the value of network state from the value of the twin's what-if search.
3. **Scenarios** (11 in total):
   - `low_quality_contributors` now corrupts training logs only.
   - `corrupted_measurements` (new) models faulty counters at the source.
   - `heavy_dropout` raised to 40% base dropout (80% at two sites), so that it is a real test.
   - `model_mismatch` (new): true service times are M/G/1 with SCV 2 while every twin assumes M/M/1.
4. **Mobility** stays inside the simulated area (reflecting boundary).

## Changes to the analysis

1. **Effect.** The relative difference of means between paired arms, with a paired percentile bootstrap CI that resamples seed pairs. The mean of per-seed ratios is reported as a sensitivity check.
2. **Rate metrics** (SLA violation, drop rate) need an absolute difference of at least 0.1 percentage point before any label other than Neutral.
3. **Comparisons.**
   - H1: FNDT vs Static, Greedy and Greedy-SR.
   - H3b (new): FNDT w/o incentive vs FL + state.
   - H2, H3, H4 and H6 are unchanged.
4. **Multiplicity.** Holm within each scenario remains the primary rule. A single global Holm family is reported as a sensitivity check.
5. **Additional metrics.**
   - Out-of-sample (next-hour) forecast loss.
   - Twin fidelity computed per site and binned by network utilisation.
   - Calibration and load statistics per scenario.
   - FL energy.
6. **Sensitivity sweeps.** 20 seeds each. Service-time variability (twin model error) is added as an axis. The default incentive weights are added to the α/β/γ grid. Paired CIs are reported for every sweep point.

## Unchanged

- The claim-safe tiers: Strong ≥ 15%, Modest 5–15%, Neutral, Regression ≤ −5%.
- p_Holm < 0.05 together with a CI that excludes 0.
- The 5% non-inferiority margin for H2.
- 30 seeds per scenario.
- The commitment to report every result, including Neutral and Regression outcomes.

## Known open design gap, reported rather than fixed

On development seeds, FL forecasts sent through a faulty reporting pipeline reach the twin without any validation. NDT-only's smoothing of noisy reports, by contrast, filters them. We report the outcome of this scenario as it is. Forecast validation at the twin is listed as future work, because adding it after seeing the result would be outcome-driven tuning.
