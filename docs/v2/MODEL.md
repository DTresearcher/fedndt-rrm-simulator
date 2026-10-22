# FNDT simulator v2 — model specification

A network-level, closed-loop simulator of joint radio and edge-compute resource management for the paper's Federated Network Digital Twin (FNDT) framework. Every equation below is implemented in `src/fndt/` and checked against its source in `tests_v2/`.

## 1. Scope

- **Abstraction level.** The simulator works at the level of resource management. It does not implement a PHY/MAC stack, HARQ, packet-level queues or a standards-compliant scheduler.
- **Control interval.** One minute, which corresponds to a Non-RT RIC loop (> 1 s; Polese et al., 2023).
- **Data.** Synthetic. Results are controlled simulation evidence, not deployment evidence.

## 2. Network and radio

| Item | Model | Source |
|---|---|---|
| Layout | 7 sites (centre + first hexagonal ring), ISD 500 m, h_BS 25 m, h_UT 1.5 m | 3GPP TR 38.901 Table 7.2-1 (UMa) |
| Path loss | UMa NLOS: max(PL_LOS, PL'_NLOS), with PL'_NLOS = 13.54 + 39.08 log10 d3D + 20 log10 fc − 0.6(h_UT − 1.5); all links NLOS (conservative); fc = 4 GHz | TR 38.901 Table 7.4.1-1; ITU-R M.2412 |
| Shadow fading | 6 dB, AR(1) correlated across slots (ρ = 0.9) | TR 38.901 (UMa NLOS σ_SF) |
| Transmit PSD | 49 dBm per 20 MHz | TR 36.814 Table A.2.1.1-2; ITU-R M.2412 Table 5 |
| Noise | −174 dBm/Hz, UE noise figure 7 dB | ITU-R M.2412 Table 5 |
| Interference | other sites at the same PSD, scaled by their previous-slot utilisation | modelling choice |
| Association | best server (strongest received power) | — |
| Spectral efficiency | SE = 0 if SINR < −10 dB; 0.6 log2(1 + SINR), capped at 4.4 bps/Hz | 3GPP TR 36.942 Annex A.1 |
| Site capacity | μ_i = B_i · SE_i, where SE_i is the demand-weighted harmonic mean over the site's users (time sharing) | — |

## 3. Traffic and mobility

- **Users.** 30 per site on average, split unevenly across sites (Dirichlet concentration 8, or 2 in high_noniid). Each user has a lognormal mean demand of 0.7 Mbit/s with σ = 0.6.
- **Diurnal pattern.** Each site carries a residential, office or mixed land-use profile, mean-normalised. This follows the distinct tower patterns reported by Xu et al. (2017); the exact shapes are an assumption. The non-IID severity ν mixes each site's own profile with the common average: (1 − ν)·average + ν·own.
- **Short-term variation.** An AR(1) lognormal fluctuation per user (φ = 0.92) makes demand forecastable but noisy.
- **Mobility.** A correlated random walk anchored at home, moving 60 m per slot (150 m in the mobility scenario). Hotspot events pull users towards the event site and raise their demand.
- **Edge workload.** Lognormal per user, with a mean of 300 cycles/bit (Mao et al., 2017).

## 4. Queueing and latency

Each site has a radio queue and an MEC queue. In slot t, with arrival rate λ, capacity μ, job size L and backlog Q:

- Backlog (Lindley-type recursion; Lindley, 1952): Q' = min(max(0, Q + (λ − μ)Δ), Q_max), with Q_max = 2 s × μ. Overflow is dropped.
- Delay = backlog wait (Q + Q')/(2μ) + M/M/1 sojourn L/(μ(1 − ρ)), with ρ = min(λ/μ, 0.98) (Kleinrock, 1975).
- End-to-end latency = radio delay + MEC delay + 4 ms backhaul.
- SLA violation probability: exact hypoexponential tail of the two exponential sojourns. Dropped traffic always counts as a violation.
- Percentiles: drawn from the same distribution (16 samples per site-slot), weighted by delivered traffic.

## 5. Strategies (the paper's taxonomy)

All strategies share the environment and the queueing model. **No strategy receives a performance factor of any kind.** They differ only in two respects.

**Information that reaches the controller.** Every report reaches the controller with the same staleness for every strategy, plus multiplicative report noise.

**Decision mechanism.**

| Strategy | Forecast of next-slot load | Network state used | Allocation |
|---|---|---|---|
| Static | – | – | equal split |
| Greedy | last report | – | proportional to last report |
| Centralized | ridge regression on pooled raw reports | channel and backlog (from raw telemetry) | twin-style what-if |
| FL-only | FedAvg model, local inference | none (nominal SE, no backlog) | Kleinrock square-root |
| NDT-only | Holt smoothing on reports (no learning) | twin state sync | twin what-if |
| FNDT w/o incentive | FedAvg model, local inference | twin state sync | twin what-if |
| FNDT | FedAvg + incentive engine, local inference | twin state sync | twin what-if |

**Kleinrock square-root assignment** (Kleinrock, 1976), with need_i = λ_i / SE_i:

B_i = need_i + (B − Σ need) · √need_i / Σ √need_j

This minimises traffic-weighted M/M/1 delay. When Σ need ≥ B the network is overloaded and the formula has no solution. The fallback keeps the least-loaded sites stable and shares the remainder in proportion to demand.

**Twin what-if.** The twin holds the synchronised state: EWMA-filtered spectral efficiency, backlog and load (Y.3090 accuracy and synchronisation requirements). For each resource it evaluates five candidate allocations with the queueing model and picks the lowest predicted latency (dropped traffic is penalised). The candidates are Kleinrock, proportional, equal, protect-smallest, and the Kleinrock/equal midpoint.

**Forecaster.** A linear model with 9 features:
- intercept;
- the last 4 lags (1, 2, 3 and 6 slots back);
- the same slot on the previous day;
- the 12-slot mean;
- time of day as sine and cosine.

Each site's series is normalised by its own recent mean. Training and inference use only data available at decision time. `test_forecast_uses_no_future_data` checks this by perturbing future data.

## 6. Federated learning and incentive engine

- **FedAvg (McMahan et al., 2017).** The model is retrained every 60 slots in 5 rounds of 2 local epochs (minibatch SGD, learning rate 0.05, batch 32). Each site trains on its own last day of locally recorded load. Updates are averaged by sample count. A site joins a round with probability 1 − dropout.
- **Faulty contributors.** Low-quality sites have multiplicative label noise in their local logs. Free-riders send random updates.
- **Incentive.** The paper's Eq. (2):

  R_i = α Q_i − β C_i + γ P_i, with α + β + γ = 1 (default 0.5 / 0.2 / 0.3)

  - **Q_i:** relative reduction of validation loss produced by the site's update. The validation set is the twin's synchronised reports, i.e. server-side validation in the spirit of FLTrust (Cao et al., 2021). Normalised to [0, 1] over the round.
  - **C_i:** device energy κ C D f² + p s / r (Yang et al., 2021), with κ = 1e-28 and 2×10⁴ cycles per sample. CPU is 1–2 GHz and uplink 5–50 Mbit/s, drawn per site. Normalised to [0, 1].
  - **P_i:** EWMA of the site's participation record (weight 0.8). This is a simplified reputation; Kang et al. (2019) use subjective logic.
- **How rewards are used.**
  - Aggregation weight = n_i · max(R_i, 0).
  - Payment is proportional to max(R_i, 0).
  - Participation = base + elasticity × (average payment) × (1 − base). Elasticity is swept over 0, 0.3 and 0.6.
- **Reward fairness.** Jain's index (Jain et al., 1984) and the coefficient of variation of cumulative payments.

## 7. Metrics

| Metric | Definition |
|---|---|
| Mean latency | traffic-weighted mean over delivered traffic |
| p95 / p99 latency | quantiles of the latency distribution |
| SLA violation rate | share of offered traffic over 100 ms or dropped |
| Drop rate | dropped / offered (buffer overflow + radio outage) |
| Throughput | radio traffic served per second |
| Jain fairness | Jain index over sites of served/offered, averaged over slots |
| Forecast fidelity | 1 − WAPE of the load forecast |
| Twin fidelity | 1 − Σ\|predicted − realised mean latency\| / Σ realised (the paper's Eq. 1, normalised error) |
| Control overhead | bytes per day of reports, raw telemetry (8 floats per user-slot), state sync (5 floats per site-slot), forecasts, model updates and broadcasts, reward signalling |
| Raw records exposed | per-user records that leave their site (only Centralized exports raw telemetry) |
| FL metrics | energy, rounds to reach within 2% of the final loss, final validation loss, participation rate |

## 8. Statistics

See `PREREGISTRATION.md` and `src/fndt/stats.py`: paired Wilcoxon, Holm correction, bootstrap CIs, d_z, A12, claim-safe labels, non-inferiority, Friedman ranks.

## 9. Limitations

- Synthetic traffic and a network-level abstraction; there is no validation against operator data.
- 7 sites; interference coupling through utilisation only.
- The MEC workload is generated independently of radio delivery.
- The forecaster is linear. FL privacy is structural only: no differential privacy or secure aggregation is implemented, and quality scoring needs per-client updates, which conflicts with secure aggregation (Bonawitz et al., 2017).
- Participation response to payment is an assumed linear elasticity, reported through a sweep.
- Twin fidelity is measured against simulator ground truth.
