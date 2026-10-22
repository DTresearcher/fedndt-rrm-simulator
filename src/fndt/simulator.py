"""Closed-loop simulation of the seven strategies of the paper's baseline taxonomy.

All strategies share one environment model and differ only in
  (a) the information that reaches the controller, and
  (b) the forecasting and allocation mechanism,
as summarised in STRATEGIES. No strategy receives a performance bonus: latency,
loss and throughput always come from the same queueing model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fndt.environment import Environment
from fndt.federated import FederatedTrainer
from fndt.forecasting import (
    FEATURE_DIM,
    Holt,
    features,
    predict_site,
    ridge_fit,
    site_scale,
    training_set,
)
from fndt.queueing import equal, kleinrock, proportional, protect_smallest, queue_step
from fndt.radio import sinr_db, spectral_efficiency


@dataclass(frozen=True)
class StrategySpec:
    name: str
    label: str
    kind: str  # heuristic | architectural
    forecaster: str  # none | last | pooled | holt | fedavg | fedavg_incentive
    twin: bool  # what-if optimisation on synchronised state (backlog, channel)
    info: str  # what crosses to the controller


STRATEGIES = (
    StrategySpec("static", "Static", "heuristic", "none", False, "nothing"),
    StrategySpec("greedy", "Greedy", "heuristic", "last", False, "per-site load reports"),
    StrategySpec("centralized", "Centralized", "architectural", "pooled", True, "raw per-user telemetry"),
    StrategySpec("fl_only", "FL-only", "architectural", "fedavg", False, "forecasts + model updates"),
    StrategySpec("ndt_only", "NDT-only", "architectural", "holt", True, "twin state sync"),
    StrategySpec("fndt_no_incentive", "FNDT w/o incentive", "architectural", "fedavg", True, "forecasts + model updates + twin state sync"),
    StrategySpec("fndt", "FNDT", "architectural", "fedavg_incentive", True, "forecasts + model updates + twin state sync + rewards"),
)
STRATEGY_BY_NAME = {s.name: s for s in STRATEGIES}

RAW_FEATURES_PER_USER = 8  # id, cell, position (2), SINR, demand, workload, timestamp
STATE_FEATURES_PER_SITE = 5  # load, workload, radio backlog, MEC backlog, spectral efficiency
BYTES_PER_FLOAT = 4
SAMPLES_PER_SITE_SLOT = 16


def _site_aggregates(env: Environment):
    """Exogenous per-site offered radio load (Mbit/s) and MEC load (Gcycle/s)."""
    T, S = env.demand.shape[0], env.n_sites
    load = np.zeros((T, S))
    cyc = np.zeros((T, S))
    for t in range(T):
        load[t] = np.bincount(env.serving[t], weights=env.demand[t], minlength=S)
        cyc[t] = np.bincount(env.serving[t], weights=env.demand[t] * env.cycles_per_bit, minlength=S) / 1000.0
    return load, cyc


def _reports(true: np.ndarray, env: Environment) -> np.ndarray:
    rep = true * env.report_noise
    for t in range(1, rep.shape[0]):
        stale = env.report_stale[t]
        rep[t, stale] = rep[t - 1, stale]
    return rep


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
        self.rep_load = _reports(self.load, env)
        self.rep_cyc = _reports(self.cyc, env)
        self.local_load = self.load * env.local_label_noise  # what each site itself records
        self.w = None
        self.trainer = None
        if spec.forecaster in ("fedavg", "fedavg_incentive"):
            self.trainer = FederatedTrainer(sc, self.S, env.seed, incentive=spec.forecaster == "fedavg_incentive")
        self.holt = Holt(self.S) if spec.forecaster == "holt" else None

    # ---------- forecasting ----------
    def _retrain(self, t: int, k: int) -> None:
        fl = self.sc.fl
        hours = self.env.hours
        if self.spec.forecaster == "pooled":
            Xs, ys = [], []
            for i in range(self.S):
                X, y, _ = training_set(self.rep_load[:, i], hours, t - self.lag + 1, fl.window_slots, self.lag, self.day)
                Xs.append(X)
                ys.append(y)
            self.w = ridge_fit(np.vstack(Xs), np.concatenate(ys))
        elif self.trainer is not None:
            local = [
                training_set(self.local_load[:, i], hours, t, fl.window_slots, self.lag, self.day)[:2]
                for i in range(self.S)
            ]
            val = self._pooled_set(self.rep_load, t - self.lag + 1, 360)
            ev = self._pooled_set(self.load, t, 360)
            self.w = self.trainer.retrain(k, local, self.env, val, ev)

    def _pooled_set(self, series, end, window):
        Xs, ys = [], []
        for i in range(self.S):
            X, y, _ = training_set(series[:, i], self.env.hours, end, window, self.lag, self.day)
            Xs.append(X)
            ys.append(y)
        return np.vstack(Xs), np.concatenate(ys)

    def _forecast(self, t: int) -> np.ndarray | None:
        f = self.spec.forecaster
        if f == "none":
            return None
        if f == "last":
            return self.rep_load[t - self.lag]
        if f == "holt":
            return self.holt.forecast(self.lag)
        series = self.rep_load if f == "pooled" else self.local_load
        return np.array(
            [predict_site(self.w, series[:, i], self.env.hours, t, self.lag, self.day, self.sc.fl.window_slots) for i in range(self.S)]
        )

    # ---------- allocation ----------
    def _candidates(self, need: np.ndarray, total: float):
        k = kleinrock(need, total)
        e = equal(self.S, total)
        return [k, proportional(need, total), e, protect_smallest(need, total), 0.5 * (k + e)]

    def _twin_choose(self, lam, mu_per_unit, backlog, job, total):
        """What-if: evaluate candidate allocations in the twin, return the best and its prediction."""
        need = (lam + backlog / self.dt) / np.maximum(mu_per_unit, 1e-6)
        best = None
        penalty_s = 2.0 * self.sc.network.buffer_s
        weights = np.maximum(lam, 1e-9)
        for alloc in self._candidates(need, total):
            step = queue_step(lam, alloc * mu_per_unit, backlog, job, self.dt, self.sc.network.buffer_s)
            drop_rate = step.dropped / self.dt
            score = (np.sum(weights * step.mean_s) + penalty_s * drop_rate.sum()) / weights.sum()
            if best is None or score < best[0]:
                best = (score, alloc, step)
        return best[1], best[2]

    def decide(self, t, se_reported, backlog_r_rep, backlog_c_rep, cyc_ratio):
        net = self.sc.network
        name = self.spec.name
        if name == "static":
            return equal(self.S, net.radio_pool_mhz), equal(self.S, net.mec_pool_ghz), None
        lam = self._forecast(t)
        if name == "greedy":
            return (
                proportional(self.rep_load[t - self.lag], net.radio_pool_mhz),
                proportional(self.rep_cyc[t - self.lag], net.mec_pool_ghz),
                None,
            )
        lam_c = lam * cyc_ratio
        job_r = self.sc.traffic.request_mbit
        job_c = job_r * cyc_ratio / 1.0
        if not self.spec.twin:  # FL-only: forecast + optimiser, no state of the network
            se = np.full(self.S, self.sc.radio.nominal_se)
            return kleinrock(lam / se, net.radio_pool_mhz), kleinrock(lam_c, net.mec_pool_ghz), None
        alloc_r, pred_r = self._twin_choose(lam, se_reported, backlog_r_rep, job_r, net.radio_pool_mhz)
        alloc_c, pred_c = self._twin_choose(lam_c, np.ones(self.S), backlog_c_rep, job_c, net.mec_pool_ghz)
        pred = (pred_r, pred_c, lam)
        return alloc_r, alloc_c, pred

    # ---------- main loop ----------
    def run(self) -> dict:
        env, sc, S, dt = self.env, self.sc, self.S, self.dt
        net, tr = sc.network, sc.traffic
        T0, T = env.warmup, env.warmup + net.slots
        rng = np.random.default_rng(env.seed + 31337)
        backlog_r = np.zeros(S)
        backlog_c = np.zeros(S)
        hist_br = np.zeros((T, S))
        hist_bc = np.zeros((T, S))
        hist_se = np.full((T, S), sc.radio.nominal_se)
        util = np.full(S, 0.6)
        if self.holt is not None:
            for t in range(T0 - self.lag + 1):
                self.holt.update(self.rep_load[t])
        cyc_ratio_hist = self.rep_cyc / np.maximum(self.rep_load, 1e-9)
        se_est = np.full(S, sc.radio.nominal_se)
        smooth = sc.telemetry.twin_state_smoothing

        acc = {k: [] for k in ("lat_sum", "w", "sla_viol", "dropped", "offered", "served", "jain", "fc_err", "fc_true", "twin_err", "twin_true")}
        samples, sample_w = [], []
        k = 0
        for t in range(T0, T):
            if self.spec.forecaster in ("pooled", "fedavg", "fedavg_incentive") and (t - T0) % sc.fl.retrain_every_slots == 0:
                self._retrain(t, k)
                k += 1
            if self.holt is not None and t - self.lag >= T0 - self.lag + 1:
                self.holt.update(self.rep_load[t - self.lag])

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
            hist_se[t] = se_site

            a = t - self.lag
            local_ratio = self.cyc[t - 1] / np.maximum(self.load[t - 1], 1e-9)
            ratio = cyc_ratio_hist[a] if self.spec.twin else local_ratio
            if a >= T0:
                se_est = (1 - smooth) * se_est + smooth * hist_se[a]
            alloc_r, alloc_c, pred = self.decide(t, se_est, hist_br[a], hist_bc[a], ratio)

            job_c = tr.request_mbit * (self.cyc[t] / np.maximum(self.load[t], 1e-9))
            qr = queue_step(carried, alloc_r * se_site, backlog_r, tr.request_mbit, dt, net.buffer_s)
            qc = queue_step(self.cyc[t], alloc_c, backlog_c, job_c, dt, net.buffer_s)
            backlog_r, backlog_c = qr.backlog_end, qc.backlog_end
            hist_br[t], hist_bc[t] = backlog_r, backlog_c
            util = qr.utilisation

            bh = net.backhaul_ms / 1000.0
            mean_s = qr.mean_s + qc.mean_s + bh
            offered = self.load[t] * dt
            dropped = qr.dropped + outage * dt
            served_frac = np.clip(1.0 - dropped / np.maximum(offered, 1e-12), 0.0, 1.0)
            w = self.load[t] * served_frac  # traffic that is actually delivered
            x = net.sla_ms / 1000.0 - (qr.wait_s + qc.wait_s + bh)
            viol = np.where(x <= 0, 1.0, hypoexp_tail(np.maximum(x, 0), qr.service_mean_s, qc.service_mean_s))
            acc["lat_sum"].append(np.sum(w * mean_s))
            acc["w"].append(w.sum())
            acc["sla_viol"].append(np.sum(w * viol) + np.sum(self.load[t] - w))
            acc["dropped"].append(dropped.sum())
            acc["offered"].append(offered.sum())
            acc["served"].append(qr.served.sum())
            sat = np.clip(qr.served / np.maximum(offered, 1e-12), 0, 1)
            acc["jain"].append(sat.sum() ** 2 / (S * np.sum(sat**2) + 1e-12))
            draw = (
                (qr.wait_s + qc.wait_s + bh)[:, None]
                + rng.exponential(1.0, (S, SAMPLES_PER_SITE_SLOT)) * qr.service_mean_s[:, None]
                + rng.exponential(1.0, (S, SAMPLES_PER_SITE_SLOT)) * qc.service_mean_s[:, None]
            )
            samples.append(draw.ravel())
            sample_w.append(np.repeat(w / SAMPLES_PER_SITE_SLOT, SAMPLES_PER_SITE_SLOT))

            if self.trace is not None:
                for key, val in (
                    ("radio_ms", 1000 * qr.mean_s), ("mec_ms", 1000 * qc.mean_s), ("radio_util", qr.utilisation),
                    ("mec_util", qc.utilisation), ("radio_backlog", backlog_r), ("alloc_mhz", alloc_r),
                    ("alloc_ghz", alloc_c), ("load", self.load[t]), ("se", se_site),
                ):
                    self.trace.setdefault(key, []).append(np.array(val, float))
            lam = self._forecast(t) if self.spec.forecaster != "none" else None
            if lam is not None:
                acc["fc_err"].append(np.abs(lam - self.load[t]).sum())
                acc["fc_true"].append(self.load[t].sum())
            if pred is not None:
                pr, pc, lam_hat = pred
                wpred = np.maximum(lam_hat, 1e-9)
                predicted = np.sum(wpred * (pr.mean_s + pc.mean_s + bh)) / wpred.sum()
                realised = np.sum(w * mean_s) / max(w.sum(), 1e-12)
                acc["twin_err"].append(abs(predicted - realised))
                acc["twin_true"].append(realised)

        lat = np.concatenate(samples)
        lw = np.concatenate(sample_w)
        res = {
            "mean_latency_ms": 1000 * sum(acc["lat_sum"]) / sum(acc["w"]),
            "p95_latency_ms": 1000 * weighted_quantile(lat, lw, 0.95),
            "p99_latency_ms": 1000 * weighted_quantile(lat, lw, 0.99),
            "sla_violation_rate": sum(acc["sla_viol"]) / (sum(acc["offered"]) / dt),
            "drop_rate": sum(acc["dropped"]) / sum(acc["offered"]),
            "throughput_mbps": sum(acc["served"]) / (net.slots * dt),
            "jain_satisfaction": float(np.mean(acc["jain"])),
            "forecast_fidelity": 1 - sum(acc["fc_err"]) / sum(acc["fc_true"]) if acc["fc_true"] else np.nan,
            "twin_fidelity": 1 - sum(acc["twin_err"]) / sum(acc["twin_true"]) if acc["twin_true"] else np.nan,
        }
        res.update(self._overhead())
        res.update(self._fl_metrics())
        return res

    def _overhead(self) -> dict:
        n_slots = self.sc.network.slots
        U = self.env.demand.shape[1]
        name = self.spec.name
        b = 0.0
        raw_records = 0
        if name == "greedy":
            b += self.S * n_slots * 2 * BYTES_PER_FLOAT
        if name == "centralized":
            raw_records = U * n_slots
            b += raw_records * RAW_FEATURES_PER_USER * BYTES_PER_FLOAT
        if self.spec.twin and name != "centralized":
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
        if self.trainer is None:
            return {k: nan for k in ("fl_energy_j", "fl_rounds_to_converge", "fl_final_loss", "participation_rate", "reward_jain", "reward_cv")}
        log = self.trainer.log
        conv = []
        for losses in log.round_loss:
            final = losses[-1]
            hit = [r for r, v in enumerate(losses) if v <= final * 1.02]
            conv.append(hit[0] + 1 if hit else len(losses))
        pay = log.payments
        jain = pay.sum() ** 2 / (self.S * np.sum(pay**2)) if self.trainer.incentive and pay.sum() > 0 else nan
        cv = pay.std() / pay.mean() if self.trainer.incentive and pay.mean() > 0 else nan
        return {
            "fl_energy_j": log.energy_j,
            "fl_rounds_to_converge": float(np.mean(conv)),
            "fl_final_loss": float(np.mean([l[-1] for l in log.round_loss])),
            "participation_rate": float(np.mean(log.participants)) / self.S,
            "reward_jain": jain,
            "reward_cv": cv,
        }


def run_all(env: Environment, strategies=STRATEGIES) -> dict[str, dict]:
    shared = _site_aggregates(env)
    return {spec.name: Run(env, spec, shared).run() for spec in strategies}


__all__ = ["STRATEGIES", "STRATEGY_BY_NAME", "Run", "run_all", "features", "site_scale", "FEATURE_DIM"]
