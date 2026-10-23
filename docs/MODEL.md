# FNDT simulator — model specification

The simulator is network-level and closed-loop. It manages joint radio and edge-compute resources for the paper's Federated Network Digital Twin (FNDT) framework.

Every equation below is implemented in `src/fndt/`. The tests in `tests/` check each one against its source, together with the integrity properties in §10.

## 1. Scope

- **Abstraction.** The simulator works at the level of resource management. It does not implement a PHY/MAC stack, HARQ, packet-level queues or a standards-compliant scheduler.
- **Resources.** The controller divides two pooled budgets across 7 sites once per minute, which corresponds to a Non-RT RIC loop (> 1 s; Polese et al., 2023).
  - Radio: 210 MHz equivalent. This abstracts a shared resource budget such as RAN sharing or a C-RAN PRB budget; it is not literal spectrum re-farming.
  - Edge compute: 98 GHz.
- **Traffic.** Synthetic. Results are controlled simulation evidence, not deployment evidence.

## 2. Network and radio

| Item | Model | Source |
|---|---|---|
| Layout | 7 sites (centre + first hexagonal ring), ISD 500 m, h_BS 25 m, h_UT 1.5 m | 3GPP TR 38.901 Table 7.2-1 (UMa) |
| Path loss | UMa NLOS: max(PL_LOS, PL'_NLOS), with PL'_NLOS = 13.54 + 39.08 log10 d3D + 20 log10 fc − 0.6(h_UT − 1.5). All links are NLOS (conservative). fc = 4 GHz | TR 38.901 Table 7.4.1-1; ITU-R M.2412 |
| Shadow fading | 6 dB, AR(1) across slots (ρ = 0.9) | TR 38.901 (UMa NLOS σ_SF) |
| Transmit PSD | 49 dBm per 20 MHz | TR 36.814 Table A.2.1.1-2; ITU-R M.2412 Table 5 |
| Noise | −174 dBm/Hz; UE noise figure 7 dB | ITU-R M.2412 Table 5 |
| Interference | Other sites at the same PSD, scaled by their previous-slot utilisation | Modelling choice |
| Association | Best server (strongest received power) | — |
| Spectral efficiency (SE) | 0 if SINR < −10 dB; otherwise min(0.6 log2(1 + SINR), 4.4) bps/Hz | 3GPP TR 36.942 Annex A.1 |
| Site capacity | μ_i = B_i · SE_i, where SE_i is the demand-weighted harmonic mean over the site's users (time sharing) | — |

## 3. Traffic and mobility

- **Users.**
  - About 30 per site, split unevenly across sites (Dirichlet concentration 8; 2 in high_noniid).
  - Each user's mean demand is lognormal: mean 0.7 Mbit/s, σ = 0.6.
- **Diurnal pattern.**
  - Each site follows a residential, office or mixed land-use profile, motivated by Xu et al. (2017). The exact shapes are an assumption.
  - Non-IID severity ν sets each site's profile to (1 − ν)·average + ν·own.
- **Short-term variation.** An AR(1) lognormal fluctuation per user, with φ = 0.92.
- **Mobility.**
  - A correlated random walk anchored at the user's home: 60 m per slot (150 m in the mobility scenario).
  - Reflected at the boundary of the simulated area.
  - Hotspot events draw users towards the event site and raise their demand.
- **Edge workload.** Lognormal per user, mean 300 cycles/bit (Mao et al., 2017).

## 4. Queueing and latency

Each site has a radio queue and an MEC queue. In slot t, with arrival rate λ, capacity μ, job size L, backlog Q and slot length Δ:

- **Backlog** (Lindley-type recursion; Lindley, 1952): Q' = min(max(0, Q + (λ − μ)Δ), Q_max), with Q_max = 2 s × μ. Overflow is dropped.
- **Delay** = backlog wait (Q + Q')/(2μ) + within-slot sojourn.
  - The sojourn uses the Pollaczek–Khinchine mean (L/μ)·(1 + ρ(1 + c²)/(2(1 − ρ))), with ρ = min(λ/μ, 0.98) (Kleinrock, 1975).
  - With service-time SCV c² = 1 (the default) this is the M/M/1 value L/(μ(1 − ρ)).
  - `model_mismatch` uses c² = 2.
- **End-to-end latency** = radio + MEC + 4 ms backhaul.
- **Delivery.** A request is delivered only if both stages serve it: delivered fraction = (1 − radio drop or outage) × (1 − MEC drop).
- **SLA violation.** The exact tail of the sum of the two exponential sojourns, plus all undelivered traffic. For c² ≠ 1 the tail is an exponential approximation with the correct mean.

## 5. Information model

All information that drives decisions passes through one explicit chain. The same chain applies to every strategy.

| Quantity | Definition |
|---|---|
| Measured (a site's own counters) | true load × measurement factor (1% noise; 60% at faulty sites in `corrupted_measurements`) |
| Training logs (FL only) | measured × log factor (60% noise at two sites in `low_quality_contributors`) |
| Delivered KPI message | measured × aggregation factor (2% noise) × pipeline factor (40% at unreliable sites). A stale event repeats the previous message (30% at unreliable sites). Every message is delayed by `staleness_slots` |
| Raw per-user telemetry (Centralized) | measured × pipeline factor, with the same stale events and delay, but no KPI aggregation noise |

- **Noise factors.** All are mean-one lognormal.
- **Decision rule.** A decision for slot t uses only information delivered up to slot t − lag, where lag = 1 + staleness. This applies to training as well as inference.
- **Messages covered.** The channel carries load reports, FL forecasts and twin state (spectral efficiency and backlog) alike.
- **Twin state estimate.** EWMA (weight 0.2) of delivered spectral efficiency, applied identically by every strategy that holds state.

## 6. Strategies

There are no per-strategy performance factors. Strategies differ only in their information and their mechanism.

| Strategy | Kind | Forecast of next-slot load | Network state | Allocation |
|---|---|---|---|---|
| Static | heuristic | – | – | equal split |
| Greedy | heuristic | last report | – | proportional to last report |
| Greedy-SR | heuristic (diagnostic) | last report | reported | Kleinrock square-root |
| Centralized | architectural | ridge regression on pooled raw telemetry | raw telemetry | twin what-if |
| FL-only | architectural | FedAvg model, forecasts sent by sites | none (nominal SE 2.0, no backlog) | Kleinrock square-root |
| FL + state | diagnostic | FedAvg model | reported | Kleinrock square-root |
| NDT-only | architectural | Holt smoothing of reports (no learning) | reported | twin what-if |
| FNDT w/o incentive | architectural | FedAvg model | reported | twin what-if |
| FNDT | architectural | FedAvg + incentive engine | reported | twin what-if |

**Kleinrock square-root assignment** (Kleinrock, 1976), with need_i = (λ_i + Q_i/Δ)/SE_i:

B_i = need_i + (B − Σ need) · √need_i / Σ √need_j

- This minimises traffic-weighted M/M/1 delay.
- Under overload (Σ need ≥ B) there is no solution. The fallback keeps the least-loaded sites stable and shares the remainder in proportion to need.

**Twin what-if.** The twin evaluates five candidate allocations per resource with its M/M/1 model and picks the lowest predicted latency, penalising predicted drops:
- Kleinrock;
- proportional;
- equal;
- protect-smallest;
- the Kleinrock/equal midpoint.

**Forecaster.** A linear model with 9 features:
- intercept;
- lags 1, 2, 3 and 6;
- the same slot on the previous day;
- the 12-slot mean;
- time of day as sine and cosine.

Each series is normalised by its own recent mean.

## 7. Federated learning and incentive engine

- **FedAvg** (McMahan et al., 2017):
  - retraining every 60 slots, in 5 rounds of 2 local epochs (SGD, learning rate 0.05, batch 32);
  - each site trains on its last day of training logs;
  - aggregation is weighted by sample count;
  - a site joins a round with probability 1 − dropout.
- **Faulty contributors.** Two sites have noisy training logs. Free-riders send random updates.
- **Incentive** (the paper's Eq. 2):

  R_i = α Q_i − β C_i + γ P_i, with α + β + γ = 1 (default 0.5 / 0.2 / 0.3)

  - **Q_i:** relative reduction of validation loss produced by the site's update. The validation set is the twin's delivered reports, i.e. server-side validation in the spirit of FLTrust (Cao et al., 2021). Normalised to [0, 1] within the round.
  - **C_i:** device energy κ C D f² + p s / r (Yang et al., 2021; Tran et al., 2019), with κ = 1e-28 and 2×10⁴ cycles per sample. CPU is 1–2 GHz and uplink 5–50 Mbit/s per site. Normalised to [0, 1].
  - **P_i:** EWMA of the site's participation record (weight 0.8). This is a simplified reputation term; Kang et al. (2019) use subjective logic.
- **How rewards are used.**
  - Aggregation weight = n_i · max(R_i, 0).
  - Payment is proportional to max(R_i, 0).
  - Participation = base + elasticity × (average payment) × (1 − base). This is an assumed response, swept over 0, 0.3 and 0.6. An unpaid site behaves exactly as it would without the incentive.
- **Reward fairness.** Jain's index of cumulative payments (Jain et al., 1984).

## 8. Metrics

| Metric | Definition |
|---|---|
| Mean, p95, p99 latency | over delivered traffic, weighted by traffic |
| SLA violation rate | share of offered traffic over 100 ms or not delivered |
| Drop rate | share of offered traffic not delivered (radio outage, radio buffer, MEC buffer) |
| Forecast fidelity | 1 − WAPE of the load forecast used for the decision |
| Out-of-sample forecast loss | MSE of each model on the following hour of true load (normalised) |
| Twin fidelity | 1 − Σ w\|predicted − realised site latency\| / Σ w·realised, with w = delivered traffic (the paper's Eq. 1). Also reported for network utilisation < 0.5, 0.5–0.8 and ≥ 0.8 |
| Control overhead | bytes per day of reports, raw telemetry (8 floats per user-slot), state (5 floats per site-slot), forecasts, model updates and broadcasts, rewards |
| Raw records exposed | per-user records that leave their site |
| Load statistics | mean and 95th-percentile site utilisation, share of saturated site-slots, peak network utilisation |
| FL | device energy, rounds to reach within 2% of the final validation loss, participation rate, reward Jain index |

## 9. Statistics

See `PREREGISTRATION.md`, `PREREGISTRATION_AMENDMENT_1.md` and `src/fndt/stats.py`.

- **Effect.** The relative difference of means between paired arms, with a paired percentile bootstrap CI.
- **Test.** Two-sided Wilcoxon signed-rank, with Holm correction per scenario. A global Holm family is reported as a sensitivity check.
- **Effect sizes.** d_z and A12.
- **Labels.** Claim-safe labels; rate metrics also need a 0.1 percentage-point floor.
- **Other analyses.** Non-inferiority for H2, and Friedman ranks across strategies.

## 10. Integrity properties checked by tests

- Determinism, and common random numbers across strategies.
- Decisions change only when delivered data changes. This is checked by perturbing undelivered data before retraining, at staleness 0 and 2.
- FL forecasts are subject to the same channel faults as load reports.
- Centralized avoids aggregation noise but not pipeline faults.
- Low-quality logs affect training only.
- Allocations use exactly the pools.
- MEC drops are counted.
- Only Centralized exports raw records.
- The incentive down-weights a free-rider.
- Twin model mismatch lowers fidelity.

## 11. Limitations

- **Simulation only.** Synthetic traffic, 7 sites and a pooled-resource abstraction; there is no validation against operator data.
- **Interference** is coupled through utilisation only.
- **The twin shares the simulator's queueing family** (M/M/1). Its fidelity therefore reflects forecast and state error, plus model error only in the mismatch scenario and sweep.
- **The forecaster is linear,** which leaves little room for learned models to differ.
- **Privacy is structural only.** No differential privacy or secure aggregation is implemented. Quality scoring needs per-client updates, which conflicts with secure aggregation (Bonawitz et al., 2017).
- **The participation response to payment is assumed.**
- **FL forecasts are not validated by the twin before use.** This is an open design gap that shows under unreliable reporting pipelines.
