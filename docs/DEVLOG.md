# Development log

All model development and checks used seeds 0–4 only. The confirmatory evidence in `results/` uses seeds 2000 and above (Amendment 1).

## Before the first confirmatory run

Every change made after the first end-to-end run, with the reason. None of
these runs used confirmatory seeds (1000 and above).

| # | Change | Reason | Effect on comparisons |
|---|---|---|---|
| 1 | Warm-up history extended from 1 to 2 days | The forecasters use the same slot of the previous day as a feature, so with a 1-day warm-up the initial training set was empty | Bug fix |
| 2 | Radio pool raised from 140 to 210 MHz (30 MHz per site) | Interference-limited spectral efficiency under load is about 1.2–1.6 bps/Hz. A 140 MHz pool saturated the whole network at peak, so every strategy failed in the same way. Calibration target: network-wide peak utilisation about 0.75 while individual sites still exceed an equal share at their own peak | Environment only; same for every strategy |
| 3 | Mean user demand set to 0.7 Mbit/s, request size 0.25 Mbit | Same calibration target; gives about 10 ms base service time per resource, typical of MEC offloading tasks (Mao et al., 2017) | Environment only |
| 4 | Twin state estimate: EWMA (weight 0.2) on reported spectral efficiency | Site spectral efficiency changes about 11% from slot to slot (fading, mobility) while site means are nearly identical. Acting on the raw last value added noise. Filtering reported state is standard state estimation | Applied identically to every strategy that holds network state: Centralized, NDT-only, FNDT w/o incentive, FNDT |
| 5 | Participation response: participation = base + elasticity × payment × (1 − base) | The first version also lowered participation of unpaid sites below the no-incentive baseline. That is an asymmetric assumption that penalised the incentive arm | Incentive arm only; makes the incentive comparison fair |
| 6 | Hotspot attraction 0.03 → 0.002 per slot, demand × 1.5 | At 0.03 nearly every user in the network joined the event, saturating every site. Target: a localised hotspot | Environment only |
| 7 | Relative improvement computed per seed: (ref − focal)/ref | Dividing by the mean across seeds let individual seeds exceed 100%, which distorted the bootstrap intervals | Analysis only |

## Observations made during development and kept unchanged

- **Low-quality-contributors scenario (superseded).** On the first information model, the incentive lowered in-sample FL loss yet raised latency. The audit traced this to a confound: the noise also corrupted inference inputs. See A2 below.
- **Baseline scenario.** The incentive had no measurable effect, as expected, because no site sends bad updates.

## After the first confirmatory run (seeds 1000–1029, superseded)

| # | Change | Reason | Effect |
|---|---|---|---|
| D1 | `abs_diff` (focal − reference, in metric units) added to every comparison | Relative improvement is unstable when the reference is close to zero (drop rates of about 1e-6), which produced extreme percentages | Reporting only. Labels, tests and p-values are unchanged |
| D2 | Docker pipeline restarted with the correct worker count | `nproc` honours `OMP_NUM_THREADS=1`, so the first launch ran on a single core. It was stopped before any output file was written | None. Same seeds, same code |

## Amendment 1: fixes from the internal audit (developed on seeds 0–4)

| # | Finding | Fix | Affected arms |
|---|---|---|---|
| A1 | FL forecasts and training used the site's own series, with no report noise and no stale messages; other arms used reports | One channel for every message to the controller (`simulator.deliver`); FL forecasts are sent through it with the same noise, stale repeats and delay | All FL arms |
| A2 | Low-quality noise was applied to the series FL used for inference | Low-quality noise now affects stored training logs only. Source-level faults are a separate scenario (`corrupted_measurements`) that affects every arm | FL arms |
| A3 | Centralized was charged for raw telemetry but used noisy site reports | Centralized aggregates raw telemetry itself: no aggregation noise, but the same delay, stale events and faulty-pipeline noise | Centralized |
| A4 | Twin state (spectral efficiency, backlog) was delivered exactly | Twin state passes the same channel; Centralized receives it via raw telemetry | Twin arms |
| A5 | FL-only's gap to the twin arms mixed state access and what-if search | Added the FL + state and Greedy-SR diagnostic arms | — |
| B1 | MEC buffer drops were not counted | Delivered traffic = radio-served fraction × MEC-served fraction | All |
| B2 | Under staleness, FL training and the compute ratio used fresher data than inference | Every learner trains and infers on data up to t − lag; tests now perturb before retraining, at staleness 0 and 2 | FL arms |
| B3 | Relative labels unstable for near-zero rates | Ratio of means with paired bootstrap; 0.1 pp floor for rate labels | Analysis |
| B4 | FL loss measured in-sample; report noise not mean-corrected; twin fidelity weighted inconsistently | Next-hour out-of-sample loss; mean-one lognormal factors; per-site fidelity weighted by delivered traffic | All |
| C1 | Under mobility, users could leave the simulated area | Reflecting boundary at the edge of the area | All |
| C2 | heavy_dropout had no measurable effect | Dropout raised to 40% (80% at two sites) | FL arms |
| C3 | Twin fidelity excluded model error | `model_mismatch` scenario and service-variability sweep (true M/G/1, twin M/M/1) | Twin arms |
| C4 | A site's faulty reporting pipeline did not affect raw telemetry | Pipeline faults affect every message from the site, including raw telemetry; only KPI aggregation noise is avoided by raw telemetry | Centralized |

## Observations on development seeds after Amendment 1, kept unchanged

- **Low-quality contributors.** With the confound removed, the incentive lowers the out-of-sample forecast loss (about 0.0133 vs 0.0181) and latency slightly.
- **Unreliable reporting pipeline.** FL forecasts arrive corrupted and are not validated by the twin, so FL-based arms fall behind NDT-only and Centralized. This is reported as a design gap, not patched (see Amendment 1).
- **Mobility.** With the boundary in place, mobility is a moderate stress scenario (about 27 ms mean latency), not a coverage collapse.
