"""Closed-loop simulation of the strategies of the paper's baseline taxonomy.

All strategies share one environment and one queueing model and differ only in
  (a) what information reaches the controller (all through the same report channel), and
  (b) the forecasting and allocation mechanism,
as listed in STRATEGIES. No strategy receives a performance factor of any kind.

Information model (docs/MODEL.md section 5):
  measured  = true load x site measurement factor            (each site's own counters)
  delivered = measured x channel factor, stale repeats, delay  (every message to the controller)
  raw       = measured x pipeline factor, stale repeats, delay; no KPI aggregation noise (Centralized only)
  logs      = measured x training-log factor                   (stored FL training data only)
A decision for slot t may use delivered information up to slot t - lag, lag = 1 + staleness.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fndt.environment import Environment
from fndt.federated import FederatedTrainer
from fndt.forecasting import FEATURE_DIM, Holt, predict_site, ridge_fit, training_set
from fndt.queueing import equal, kleinrock, proportional, protect_smallest, queue_step
from fndt.radio import sinr_db, spectral_efficiency


@dataclass(frozen=True)
class StrategySpec:
    name: str
    label: str
    kind: str  # heuristic | architectural | diagnostic
    forecaster: str  # none | last | pooled | holt | fedavg | fedavg_incentive
    state: str  # none | reported | raw : channel quality and backlog known to the controller
    allocator: str  # equal | proportional | kleinrock | whatif
    info: str


STRATEGIES = (
    StrategySpec("static", "Static", "heuristic", "none", "none", "equal", "nothing"),
    StrategySpec("greedy", "Greedy", "heuristic", "last", "none", "proportional", "load reports"),
    StrategySpec("greedy_sr", "Greedy-SR", "heuristic", "last", "reported", "kleinrock", "load + channel reports"),
    StrategySpec("centralized", "Centralized", "architectural", "pooled", "raw", "whatif", "raw per-user telemetry"),
    StrategySpec("fl_only", "FL-only", "architectural", "fedavg", "none", "kleinrock", "forecasts + model updates"),
    StrategySpec("fl_state", "FL + state", "diagnostic", "fedavg", "reported", "kleinrock", "forecasts + model updates + state reports"),
    StrategySpec("ndt_only", "NDT-only", "architectural", "holt", "reported", "whatif", "twin state sync"),
    StrategySpec("fndt_no_incentive", "FNDT w/o incentive", "architectural", "fedavg", "reported", "whatif", "forecasts + model updates + twin state sync"),
    StrategySpec("fndt", "FNDT", "architectural", "fedavg_incentive", "reported", "whatif", "forecasts + model updates + twin state sync + rewards"),
)
STRATEGY_BY_NAME = {s.name: s for s in STRATEGIES}

RAW_FEATURES_PER_USER = 8  # id, cell, position (2), SINR, demand, workload, timestamp
STATE_FEATURES_PER_SITE = 5  # load, workload, radio backlog, MEC backlog, spectral efficiency
BYTES_PER_FLOAT = 4
SAMPLES_PER_SITE_SLOT = 16
UTIL_BINS = ((0.0, 0.5, "lt50"), (0.5, 0.8, "50to80"), (0.8, 10.0, "ge80"))


def _site_aggregates(env: Environment):
    """Exogenous per-site offered radio load (Mbit/s) and MEC load (Gcycle/s)."""
    T, S = env.demand.shape[0], env.n_sites
    load = np.zeros((T, S))
    cyc = np.zeros((T, S))
    for t in range(T):
        load[t] = np.bincount(env.serving[t], weights=env.demand[t], minlength=S)
        cyc[t] = np.bincount(env.serving[t], weights=env.demand[t] * env.cycles_per_bit, minlength=S) / 1000.0
    return load, cyc


def deliver(series: np.ndarray, env: Environment, noisy: bool = True) -> np.ndarray:
    """Pass a per-slot, per-site series through the report channel (index = send slot).

    noisy=True: KPI messages (aggregation noise and pipeline faults).
    noisy=False: raw per-user telemetry, aggregated centrally (pipeline faults only).
    """
    out = series * (env.channel_noise if noisy else env.pipeline_noise)
    for t in range(1, out.shape[0]):
        stale = env.channel_stale[t]
        out[t, stale] = out[t - 1, stale]
    return out


def hypoexp_tail(x, m1, m2):
    """P(X1 + X2 > x) for independent exponentials with means m1, m2 (x >= 0)."""
    m1 = np.maximum(m1, 1e-12)
    m2 = np.maximum(m2, 1e-12)
    same = np.isclose(m1, m2, rtol=1e-6)
    a = np.exp(-x / m1)
    b = np.exp(-x / m2)
    diff = np.where(same, 1.0, m1 - m2)
    general = (m1 * a - m2 * b) / diff
    equal_case = (1 + x / m1) * a
    return np.clip(np.where(same, equal_case, general), 0.0, 1.0)


def weighted_quantile(values, weights, q):
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cw = np.cumsum(w)
    return np.interp(q * cw[-1], cw, v)


class Run:
    """One strategy on one environment realisation."""

    def __init__(self, env: Environment, spec: StrategySpec, shared=None, trace: bool = False):
        self.env, self.spec = env, spec
        self.trace = {} if trace else None
        sc = env.scenario
        self.sc = sc
        self.S = env.n_sites
        self.dt = sc.network.slot_s
        self.lag = 1 + sc.telemetry.staleness_slots
        self.day = int(round(86400 / self.dt))
        self.load, self.cyc = shared if shared is not None else _site_aggregates(env)
        self.meas_load = self.load * env.measurement
        self.meas_cyc = self.cyc * env.measurement
        self.rep_load = deliver(self.meas_load, env)
        self.rep_cyc = deliver(self.meas_cyc, env)
        self.raw_load = deliver(self.meas_load, env, noisy=False)
        self.raw_cyc = deliver(self.meas_cyc, env, noisy=False)
        self.logs = self.meas_load * env.training_log_noise
        self.w = None
        self.prev_model = None  # (weights, retrain slot) for out-of-sample evaluation
        self.oos = []
        self.trainer = None
        if spec.forecaster in ("fedavg", "fedavg_incentive"):
            self.trainer = FederatedTrainer(sc, self.S, env.seed, incentive=spec.forecaster == "fedavg_incentive")
        self.holt = Holt(self.S) if spec.forecaster == "holt" else None
        self.fc_delivered = None  # last forecast received from each site (FL strategies)

    # ---------- forecasting ----------
    def _pooled_set(self, series, end, window):
        Xs, ys = [], []
        for i in range(self.S):
            X, y, _ = training_set(series[:, i], self.env.hours, end, window, self.lag, self.day)
            Xs.append(X)
            ys.append(y)
        return np.vstack(Xs), np.concatenate(ys)

    def _retrain(self, t: int, k: int) -> None:
        fl = self.sc.fl
        end = t - self.lag + 1  # targets up to the last delivered slot t - lag
        if self.prev_model is not None:  # next-hour, out-of-sample loss on true load
            w_prev, t_prev = self.prev_model
            X, y = self._pooled_set(self.load, t, t - t_prev)
            r = X @ w_prev - y
            self.oos.append(float(np.mean(r * r)))
        if self.spec.forecaster == "pooled":
            X, y = self._pooled_set(self.raw_load, end, fl.window_slots)
            self.w = ridge_fit(X, y)
        else:
            local = [training_set(self.logs[:, i], self.env.hours, end, fl.window_slots, self.lag, self.day)[:2] for i in range(self.S)]
            val = self._pooled_set(self.rep_load, end, 360)  # the twin's synchronised reports
            self.w = self.trainer.retrain(k, local, self.env, val)
        self.prev_model = (self.w.copy(), t)

    def _forecast(self, t: int) -> np.ndarray | None:
        f = self.spec.forecaster
        a = t - self.lag
        if f == "none":
            return None
        if f == "last":
            return self.rep_load[a]
        if f == "holt":
            return self.holt.forecast(self.lag)
        if f == "pooled":
            return np.array([predict_site(self.w, self.raw_load[:, i], self.env.hours, t, self.lag, self.day, self.sc.fl.window_slots) for i in range(self.S)])
        # Federated: each site forecasts from its own counters and sends the value through the channel.
        local = np.array([predict_site(self.w, self.meas_load[:, i], self.env.hours, t, self.lag, self.day, self.sc.fl.window_slots) for i in range(self.S)])
        sent = local * self.env.channel_noise[a]
        if self.fc_delivered is not None:
            stale = self.env.channel_stale[a]
            sent[stale] = self.fc_delivered[stale]
        self.fc_delivered = sent
        return sent

    # ---------- allocation ----------
    def _candidates(self, need: np.ndarray, total: float):
        k = kleinrock(need, total)
        e = equal(self.S, total)
        return [k, proportional(need, total), e, protect_smallest(need, total), 0.5 * (k + e)]

    def _twin_choose(self, lam, mu_per_unit, backlog, job, total):
        """What-if: evaluate candidate allocations in the twin (M/M/1 model), return the best."""
        need = (lam + backlog / self.dt) / np.maximum(mu_per_unit, 1e-6)
        best = None
        penalty_s = 2.0 * self.sc.network.buffer_s
        weights = np.maximum(lam, 1e-9)
        for alloc in self._candidates(need, total):
            step = queue_step(lam, alloc * mu_per_unit, backlog, job, self.dt, self.sc.network.buffer_s)
            score = (np.sum(weights * step.mean_s) + penalty_s * (step.dropped / self.dt).sum()) / weights.sum()
            if best is None or score < best[0]:
                best = (score, alloc, step)
        return best[1], best[2]

    def decide(self, t, lam, se_est, backlog_r, backlog_c, ratio):
        net = self.sc.network
        a = t - self.lag
        alloc = self.spec.allocator
        if alloc == "equal":
            return equal(self.S, net.radio_pool_mhz), equal(self.S, net.mec_pool_ghz), None
        if alloc == "proportional":
            return proportional(self.rep_load[a], net.radio_pool_mhz), proportional(self.rep_cyc[a], net.mec_pool_ghz), None
        lam_c = lam * ratio
        if alloc == "kleinrock":
            if self.spec.state == "none":
                se = np.full(self.S, self.sc.radio.nominal_se)
                return kleinrock(lam / se, net.radio_pool_mhz), kleinrock(lam_c, net.mec_pool_ghz), None
            need_r = (lam + backlog_r / self.dt) / np.maximum(se_est, 1e-6)
            return kleinrock(need_r, net.radio_pool_mhz), kleinrock(lam_c + backlog_c / self.dt, net.mec_pool_ghz), None
        job_r = self.sc.traffic.request_mbit
        alloc_r, pred_r = self._twin_choose(lam, se_est, backlog_r, job_r, net.radio_pool_mhz)
        alloc_c, pred_c = self._twin_choose(lam_c, np.ones(self.S), backlog_c, job_r * ratio, net.mec_pool_ghz)
        return alloc_r, alloc_c, (pred_r, pred_c)

    # ---------- main loop ----------
    def run(self) -> dict:
        env, sc, S, dt = self.env, self.sc, self.S, self.dt
        net, tr = sc.network, sc.traffic
        T0, T = env.warmup, env.warmup + net.slots
        rng = np.random.default_rng(env.seed + 31337)
        backlog_r = np.zeros(S)
        backlog_c = np.zeros(S)
        hist = {"se": np.full((T, S), sc.radio.nominal_se), "br": np.zeros((T, S)), "bc": np.zeros((T, S))}
        dlv = {k: v.copy() for k, v in hist.items()}  # delivered state (index = send slot)
        noisy_state = self.spec.state == "reported"
        se_est = np.full(S, sc.radio.nominal_se)
        smooth = sc.telemetry.twin_state_smoothing
        util = np.full(S, 0.6)
        if self.holt is not None:
            for t in range(T0 - self.lag + 1):
                self.holt.update(self.rep_load[t])
        src_load, src_cyc = (self.raw_load, self.raw_cyc) if self.spec.state == "raw" else (self.rep_load, self.rep_cyc)
        ratio_hist = src_cyc / np.maximum(src_load, 1e-9)
        bh = net.backhaul_ms / 1000.0

        acc = {k: 0.0 for k in ("lat", "w", "viol", "dropped", "offered", "served_mbit", "fc_err", "fc_true", "tw_err", "tw_true")}
        bins = {name: [0.0, 0.0] for _, _, name in UTIL_BINS}
        jain, site_util, net_util, samples, sample_w = [], [], [], [], []
        k = 0
        for t in range(T0, T):
            a = t - self.lag
            if self.spec.forecaster in ("pooled", "fedavg", "fedavg_incentive") and (t - T0) % sc.fl.retrain_every_slots == 0:
                self._retrain(t, k)
                k += 1
            if self.holt is not None and a >= T0 - self.lag + 1:
                self.holt.update(self.rep_load[a])
            # State delivered for slot a (known only after slot a has finished).
            if a >= T0:
                for key in ("se", "br", "bc"):
                    value = hist[key][a] * (env.channel_noise[a] if noisy_state else env.pipeline_noise[a])
                    stale = env.channel_stale[a]
                    value[stale] = dlv[key][a - 1][stale]
                    dlv[key][a] = value
                se_est = (1 - smooth) * se_est + smooth * dlv["se"][a]

            # Channel this slot (interference from last slot's utilisation).
            users = env.serving[t]
            rx = env.rx_dbm[t].astype(float)
            sinr = sinr_db(rx[np.arange(len(users)), users], rx, users, util, sc.radio)
            se_u = spectral_efficiency(sinr, sc.radio)
            dem = env.demand[t]
            ok = se_u > 0
            outage = np.bincount(users[~ok], weights=dem[~ok], minlength=S)
            time_share = np.bincount(users[ok], weights=dem[ok] / se_u[ok], minlength=S)
            carried = np.bincount(users[ok], weights=dem[ok], minlength=S)
            se_site = np.where(time_share > 0, carried / np.maximum(time_share, 1e-12), sc.radio.nominal_se)
            hist["se"][t] = se_site

            lam = self._forecast(t)
            alloc_r, alloc_c, pred = self.decide(t, lam, se_est, dlv["br"][a], dlv["bc"][a], ratio_hist[a])

            job_c = tr.request_mbit * (self.cyc[t] / np.maximum(self.load[t], 1e-9))
            qr = queue_step(carried, alloc_r * se_site, backlog_r, tr.request_mbit, dt, net.buffer_s, net.service_scv)
            qc = queue_step(self.cyc[t], alloc_c, backlog_c, job_c, dt, net.buffer_s, net.service_scv)
            backlog_r, backlog_c = qr.backlog_end, qc.backlog_end
            hist["br"][t], hist["bc"][t] = backlog_r, backlog_c
            util = qr.utilisation

            offered = self.load[t] * dt
            radio_ok = np.clip(1.0 - (qr.dropped + outage * dt) / np.maximum(offered, 1e-12), 0.0, 1.0)
            mec_ok = np.clip(1.0 - qc.dropped / np.maximum(self.cyc[t] * dt, 1e-12), 0.0, 1.0)
            served_frac = radio_ok * mec_ok  # a request is delivered only if both stages serve it
            w = self.load[t] * served_frac
            mean_s = qr.mean_s + qc.mean_s + bh
            x = net.sla_ms / 1000.0 - (qr.wait_s + qc.wait_s + bh)
            viol = np.where(x <= 0, 1.0, hypoexp_tail(np.maximum(x, 0), qr.service_mean_s, qc.service_mean_s))
            acc["lat"] += np.sum(w * mean_s)
            acc["w"] += w.sum()
            acc["viol"] += np.sum(w * viol) + np.sum(self.load[t] - w)
            acc["dropped"] += np.sum(offered * (1.0 - served_frac))
            acc["offered"] += offered.sum()
            acc["served_mbit"] += qr.served.sum()
            sat = np.clip(qr.served / np.maximum(offered, 1e-12), 0, 1)
            jain.append(sat.sum() ** 2 / (S * np.sum(sat**2) + 1e-12))
            site_util.append(qr.utilisation)
            nu = carried.sum() / max(np.sum(alloc_r * se_site), 1e-9)
            net_util.append(nu)
            draw = (
                (qr.wait_s + qc.wait_s + bh)[:, None]
                + rng.exponential(1.0, (S, SAMPLES_PER_SITE_SLOT)) * qr.service_mean_s[:, None]
                + rng.exponential(1.0, (S, SAMPLES_PER_SITE_SLOT)) * qc.service_mean_s[:, None]
            )
            samples.append(draw.ravel())
            sample_w.append(np.repeat(w / SAMPLES_PER_SITE_SLOT, SAMPLES_PER_SITE_SLOT))
            if lam is not None:
                acc["fc_err"] += np.abs(lam - self.load[t]).sum()
                acc["fc_true"] += self.load[t].sum()
            if pred is not None:
                predicted = pred[0].mean_s + pred[1].mean_s + bh  # twin's per-site latency prediction
                err, true = np.sum(w * np.abs(predicted - mean_s)), np.sum(w * mean_s)
                acc["tw_err"] += err
                acc["tw_true"] += true
                for lo, hi, name in UTIL_BINS:
                    if lo <= nu < hi:
                        bins[name][0] += err
                        bins[name][1] += true
            if self.trace is not None:
                for key, val in (("radio_ms", 1000 * qr.mean_s), ("mec_ms", 1000 * qc.mean_s), ("radio_util", qr.utilisation),
                                 ("mec_util", qc.utilisation), ("alloc_mhz", alloc_r), ("alloc_ghz", alloc_c), ("load", self.load[t]), ("se", se_site)):
                    self.trace.setdefault(key, []).append(np.array(val, float))

        lat = np.concatenate(samples)
        lw = np.concatenate(sample_w)
        su = np.array(site_util)
        res = {
            "mean_latency_ms": 1000 * acc["lat"] / acc["w"],
            "p95_latency_ms": 1000 * weighted_quantile(lat, lw, 0.95),
            "p99_latency_ms": 1000 * weighted_quantile(lat, lw, 0.99),
            "sla_violation_rate": acc["viol"] / (acc["offered"] / dt),
            "drop_rate": acc["dropped"] / acc["offered"],
            "throughput_mbps": acc["served_mbit"] / (net.slots * dt),
            "jain_satisfaction": float(np.mean(jain)),
            "forecast_fidelity": 1 - acc["fc_err"] / acc["fc_true"] if acc["fc_true"] else np.nan,
            "twin_fidelity": 1 - acc["tw_err"] / acc["tw_true"] if acc["tw_true"] else np.nan,
            "mean_site_util": float(su.mean()),
            "p95_site_util": float(np.percentile(su, 95)),
            "saturated_site_slots": float((su >= 0.999).mean()),
            "peak_network_util": float(np.max(net_util)),
            "forecast_loss_oos": float(np.mean(self.oos)) if self.oos else np.nan,
        }
        twin = self.spec.allocator == "whatif"
        for _, _, name in UTIL_BINS:
            e, tr_ = bins[name]
            res[f"twin_fidelity_util_{name}"] = 1 - e / tr_ if twin and tr_ > 0 else np.nan
        res.update(self._overhead())
        res.update(self._fl_metrics())
        return res

    def _overhead(self) -> dict:
        n_slots = self.sc.network.slots
        U = self.env.demand.shape[1]
        spec = self.spec
        b = 0.0
        raw_records = 0
        if spec.forecaster == "last":
            b += self.S * n_slots * (3 if spec.state == "reported" else 2) * BYTES_PER_FLOAT
        if spec.state == "raw":
            raw_records = U * n_slots
            b += raw_records * RAW_FEATURES_PER_USER * BYTES_PER_FLOAT
        if spec.state == "reported" and spec.forecaster != "last":
            b += self.S * n_slots * STATE_FEATURES_PER_SITE * BYTES_PER_FLOAT
        if self.trainer is not None:
            b += self.S * n_slots * 2 * BYTES_PER_FLOAT  # forecasts sent to the allocator
            rounds = len(self.trainer.log.participants)
            b += 2 * self.trainer.log.uplink_updates * FEATURE_DIM * BYTES_PER_FLOAT
            b += rounds * self.S * FEATURE_DIM * BYTES_PER_FLOAT  # model broadcast
            if self.trainer.incentive:
                b += self.trainer.log.uplink_updates * 3 * BYTES_PER_FLOAT
        return {"overhead_mb": b / 1e6, "raw_records_exposed": raw_records}

    def _fl_metrics(self) -> dict:
        nan = float("nan")
        keys = ("fl_energy_j", "fl_rounds_to_converge", "participation_rate", "reward_jain", "reward_cv")
        if self.trainer is None:
            return {k: nan for k in keys}
        log = self.trainer.log
        conv = []
        for losses in log.round_loss:
            final = losses[-1]
            hit = [r for r, v in enumerate(losses) if v <= final * 1.02]
            conv.append(hit[0] + 1 if hit else len(losses))
        pay = log.payments
        inc = self.trainer.incentive and pay.sum() > 0
        return {
            "fl_energy_j": log.energy_j,
            "fl_rounds_to_converge": float(np.mean(conv)),
            "participation_rate": float(np.mean(log.participants)) / self.S,
            "reward_jain": pay.sum() ** 2 / (self.S * np.sum(pay**2)) if inc else nan,
            "reward_cv": pay.std() / pay.mean() if inc else nan,
        }


def run_all(env: Environment, strategies=STRATEGIES) -> dict[str, dict]:
    shared = _site_aggregates(env)
    return {spec.name: Run(env, spec, shared).run() for spec in strategies}
