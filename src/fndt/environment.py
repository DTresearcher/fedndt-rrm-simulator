"""Exogenous environment: users, mobility, traffic, channel and telemetry faults.

Everything random is drawn here, once per seed, before any strategy runs.
All strategies then face exactly the same realisation (common random numbers,
Law 2015), so differences between strategies come from their decisions only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fndt.config import Scenario
from fndt.radio import hex_sites, uma_nlos_db

PROFILE_NAMES = ("residential", "office", "mixed")


def _bump(hours: np.ndarray, centre: float, width: float) -> np.ndarray:
    d = np.minimum(np.abs(hours - centre), 24.0 - np.abs(hours - centre))
    return np.exp(-0.5 * (d / width) ** 2)


def diurnal_profiles(hours: np.ndarray) -> np.ndarray:
    """Land-use traffic profiles (rows: residential, office, mixed), mean 1.

    Shapes follow the distinct residential, office and transport/mixed tower
    patterns reported by Xu et al. (2017); exact shapes are a modelling assumption.
    """
    res = 0.35 + 0.25 * _bump(hours, 8.5, 1.5) + 1.0 * _bump(hours, 21.0, 2.5)
    off = 0.25 + 0.9 * _bump(hours, 11.0, 2.0) + 0.8 * _bump(hours, 15.5, 2.0)
    mix = 0.35 + 0.8 * _bump(hours, 8.5, 1.2) + 0.9 * _bump(hours, 18.0, 1.5) + 0.3 * _bump(hours, 13.0, 2.0)
    prof = np.vstack([res, off, mix])
    return prof / prof.mean(axis=1, keepdims=True)


@dataclass
class Environment:
    scenario: Scenario
    seed: int
    sites_xy: np.ndarray  # (S, 2)
    site_profile: np.ndarray  # (S,) index into PROFILE_NAMES
    hours: np.ndarray  # (T,) hour of day of every slot, warm-up included
    serving: np.ndarray  # (T, U) serving site
    demand: np.ndarray  # (T, U) offered traffic, Mbit/s
    rx_dbm: np.ndarray  # (T, U, S) received PSD from every site, dBm/MHz
    cycles_per_bit: np.ndarray  # (U,)
    report_noise: np.ndarray  # (T, S) multiplicative report factor
    report_stale: np.ndarray  # (T, S) bool: unreliable site repeats last report
    local_label_noise: np.ndarray  # (T, S) multiplicative factor on local training data
    fl_uniforms: np.ndarray  # (n_retrain, rounds, S) participation draws
    fl_seeds: np.ndarray  # (n_retrain,) seeds for local SGD shuffling
    free_rider_noise: np.ndarray  # (n_retrain, rounds, S, D) random updates

    @property
    def n_sites(self) -> int:
        return self.sites_xy.shape[0]

    @property
    def warmup(self) -> int:
        return self.scenario.network.warmup_slots


FEATURE_DIM = 9  # must match forecasting.FEATURE_DIM


def build_environment(scenario: Scenario, seed: int) -> Environment:
    rng = np.random.default_rng(seed)
    net, tr, rp, tm, fl = scenario.network, scenario.traffic, scenario.radio, scenario.telemetry, scenario.fl
    S = net.n_sites
    T = net.warmup_slots + net.slots
    sites = hex_sites(S, rp.isd_m)
    hours = (np.arange(T) * net.slot_s / 3600.0) % 24.0

    profiles = diurnal_profiles(hours)  # (3, T)
    site_profile = rng.permutation(np.arange(S) % len(PROFILE_NAMES))
    common = profiles.mean(axis=0)
    site_curve = (1.0 - tr.noniid) * common[None, :] + tr.noniid * profiles[site_profile]  # (S, T)

    # Users: uneven split across sites, positions around the home site.
    popularity = rng.dirichlet(np.full(S, tr.site_popularity_conc))
    U = tr.users_per_site * S
    home = rng.choice(S, size=U, p=popularity)
    radius = rp.isd_m / np.sqrt(3.0)
    r0 = radius * np.sqrt(rng.uniform(0.02, 1.0, U))
    a0 = rng.uniform(0, 2 * np.pi, U)
    anchor = sites[home] + np.c_[r0 * np.cos(a0), r0 * np.sin(a0)]
    pos = anchor.copy()

    scale = tr.mean_user_mbps * tr.load_scale * rng.lognormal(-0.5 * tr.user_scale_sigma**2, tr.user_scale_sigma, U)
    cycles_per_bit = tr.cycles_per_bit_mean * rng.lognormal(-0.5 * tr.cycles_per_bit_sigma**2, tr.cycles_per_bit_sigma, U)

    serving = np.empty((T, U), dtype=np.int16)
    demand = np.empty((T, U))
    rx_dbm = np.empty((T, U, S), dtype=np.float32)
    shadow = rng.normal(0, rp.shadow_std_db, (U, S))
    x = rng.normal(0, tr.ar_sigma, U)
    heading = rng.uniform(0, 2 * np.pi, U)
    at_event = np.zeros(U, dtype=bool)
    hot = np.array(tr.hotspot_sites, dtype=int)

    for t in range(T):
        h = hours[t]
        event_on = hot.size > 0 and tr.hotspot_start_h <= h < tr.hotspot_end_h
        if event_on and tr.hotspot_attraction > 0:
            joiners = (~at_event) & (rng.random(U) < tr.hotspot_attraction)
            at_event |= joiners
        elif not event_on:
            at_event[:] = False
        target = anchor.copy()
        if at_event.any():
            event_xy = sites[hot[np.arange(U) % hot.size]]
            target[at_event] = event_xy[at_event]
        # Correlated random walk pulled towards the user's current anchor.
        heading += rng.normal(0, 0.6, U)
        step = tr.speed_m_per_slot * np.c_[np.cos(heading), np.sin(heading)]
        pos = pos + step + 0.15 * (target - pos)
        d2d = np.linalg.norm(pos[:, None, :] - sites[None, :, :], axis=2)
        shadow = rp.shadow_corr * shadow + np.sqrt(1 - rp.shadow_corr**2) * rng.normal(0, rp.shadow_std_db, (U, S))
        rx = rp.tx_dbm_per_mhz - uma_nlos_db(d2d, rp) + shadow
        rx_dbm[t] = rx
        serving[t] = np.argmax(rx, axis=1)  # best-server association
        x = tr.ar_phi * x + np.sqrt(1 - tr.ar_phi**2) * rng.normal(0, tr.ar_sigma, U)
        level = site_curve[serving[t], t] * scale * np.exp(x - 0.5 * tr.ar_sigma**2)
        if event_on:
            level = np.where(np.isin(serving[t], hot), level * tr.hotspot_multiplier, level)
        demand[t] = level

    report_noise = rng.lognormal(0, tm.report_noise, (T, S))
    report_stale = np.zeros((T, S), dtype=bool)
    local_label_noise = np.ones((T, S))
    if tm.unreliable_sites:
        idx = np.array(tm.unreliable_sites)
        report_noise[:, idx] *= rng.lognormal(0, max(tm.unreliable_noise, 1e-9), (T, idx.size))
        report_stale[:, idx] = rng.random((T, idx.size)) < tm.stale_prob
        if tm.corrupt_local_data:
            local_label_noise[:, idx] = rng.lognormal(0, max(tm.unreliable_noise, 1e-9), (T, idx.size))
    if fl.low_quality_sites:
        idx = np.array(fl.low_quality_sites)
        local_label_noise[:, idx] *= rng.lognormal(0, max(fl.low_quality_noise, 1e-9), (T, idx.size))

    n_retrain = net.slots // fl.retrain_every_slots + 2
    fl_uniforms = rng.random((n_retrain, fl.rounds, S))
    fl_seeds = rng.integers(0, 2**31 - 1, n_retrain)
    free_rider_noise = rng.normal(0, 0.5, (n_retrain, fl.rounds, S, FEATURE_DIM))

    return Environment(
        scenario=scenario,
        seed=seed,
        sites_xy=sites,
        site_profile=site_profile,
        hours=hours,
        serving=serving,
        demand=demand,
        rx_dbm=rx_dbm,
        cycles_per_bit=cycles_per_bit,
        report_noise=report_noise,
        report_stale=report_stale,
        local_label_noise=local_label_noise,
        fl_uniforms=fl_uniforms,
        fl_seeds=fl_seeds,
        free_rider_noise=free_rider_noise,
    )
