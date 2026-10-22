# Development log (seeds 0–4 only)

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

- **Low-quality-contributors scenario.** The incentive lowered the FL validation loss by about 40%, yet slightly increased latency. The cleaner global model relies more on lagged inputs, and the low-quality sites feed it noisy local inputs at inference. This is reported as a finding; it is not a bug.
- **Baseline scenario.** The incentive had no measurable effect, as expected, because no site sends bad updates.
