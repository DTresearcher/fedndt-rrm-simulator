"""Scenario configuration.

Every numeric parameter of the model lives here, with its source noted where
one exists. Scenario YAML files override fields by name; anything not given
keeps the default below. See docs/MODEL.md for the equations.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RadioParams:
    # 3GPP TR 38.901 V17.0.0, Table 7.4.1-1 (UMa) and Table 7.2-1 (layout).
    carrier_ghz: float = 4.0  # ITU-R M.2412 Urban Macro evaluation carrier
    isd_m: float = 500.0
    h_bs_m: float = 25.0
    h_ut_m: float = 1.5
    shadow_std_db: float = 6.0  # UMa NLOS sigma_SF
    shadow_corr: float = 0.9  # slot-to-slot AR(1) correlation of shadowing
    # Transmit PSD: 49 dBm per 20 MHz (TR 36.814 Table A.2.1.1-2; M.2412 Table 5).
    tx_dbm_per_mhz: float = 49.0 - 13.0103
    # Thermal noise -174 dBm/Hz; UE noise figure 7 dB (ITU-R M.2412 Table 5).
    noise_dbm_per_mhz: float = -174.0 + 60.0 + 7.0
    # Attenuated, truncated Shannon bound, 3GPP TR 36.942 Annex A.1 (downlink).
    shannon_alpha: float = 0.6
    snr_min_db: float = -10.0
    se_max: float = 4.4
    # Spectral efficiency assumed by controllers that receive no channel state.
    nominal_se: float = 2.0


@dataclass
class TrafficParams:
    users_per_site: int = 30
    # Heterogeneity of users across sites (Dirichlet concentration; lower = more skewed).
    site_popularity_conc: float = 8.0
    mean_user_mbps: float = 0.7
    user_scale_sigma: float = 0.6  # lognormal spread of per-user mean demand
    ar_phi: float = 0.92  # slot-to-slot correlation of demand fluctuation
    ar_sigma: float = 0.25
    load_scale: float = 1.0  # traffic-pressure multiplier (sensitivity axis)
    # Non-IID severity in [0, 1]: 0 = all sites share one diurnal profile,
    # 1 = each site follows its own land-use profile (residential/office/mixed).
    noniid: float = 0.6
    request_mbit: float = 0.25  # mean request size (M/M/1 job size)
    cycles_per_bit_mean: float = 300.0  # MEC workload (Mao et al., 2017)
    cycles_per_bit_sigma: float = 0.4
    speed_m_per_slot: float = 60.0  # pedestrian, about 3.6 km/h over 60 s
    # Hotspot event: users drift towards the event site and its demand rises.
    hotspot_sites: list[int] = field(default_factory=list)
    hotspot_start_h: float = 17.0
    hotspot_end_h: float = 21.0
    hotspot_multiplier: float = 1.0
    hotspot_attraction: float = 0.0  # per-slot probability a user heads to the event


@dataclass
class NetworkParams:
    n_sites: int = 7  # centre site plus first ring of a hexagonal grid
    slot_s: float = 60.0  # Non-RT control interval (>1 s, O-RAN Non-RT RIC)
    slots: int = 1440  # evaluated day
    warmup_slots: int = 2880  # two history days: one for seasonal lags, one for training
    radio_pool_mhz: float = 210.0  # pooled radio resource (equal share 30 MHz per site)
    mec_pool_ghz: float = 98.0  # pooled edge compute (equal share 14 GHz)
    buffer_s: float = 2.0  # buffer holds this many seconds of service; excess is dropped
    backhaul_ms: float = 4.0
    sla_ms: float = 100.0
    # Squared coefficient of variation of true service times. 1 = exponential (M/M/1);
    # other values give M/G/1 (Pollaczek-Khinchine) while the twin keeps assuming M/M/1.
    service_scv: float = 1.0


@dataclass
class TelemetryParams:
    """Information model (MODEL.md section 5).

    measurement: each site's own counters = true load x measurement factor.
    report channel: everything a site sends to the controller (load reports,
    FL forecasts, twin state) = measured value x channel factor, delayed by
    staleness_slots, and repeated from the previous message when a stale event
    occurs. Raw per-user telemetry (Centralized) is aggregated centrally, so it
    carries no KPI aggregation noise (report_noise) but suffers the same delays,
    stale events and faulty-pipeline noise (unreliable_noise) as every other message.
    """

    staleness_slots: int = 0  # delivery delay of every message to the controller
    report_noise: float = 0.02  # aggregation/reporting noise (lognormal std, mean-corrected)
    unreliable_sites: list[int] = field(default_factory=list)
    stale_prob: float = 0.0  # unreliable sites: probability a message is a stale repeat
    unreliable_noise: float = 0.0  # unreliable sites: faulty reporting pipeline, affects all their messages
    measurement_noise: float = 0.01  # error of every site's own counters
    corrupted_sites: list[int] = field(default_factory=list)  # faulty counters at the source
    corrupted_noise: float = 0.0
    # Twin state estimation: EWMA weight on each new channel/backlog report. Fixed on
    # development seeds and applied to every strategy that holds network state.
    twin_state_smoothing: float = 0.2


@dataclass
class FLParams:
    retrain_every_slots: int = 60
    rounds: int = 5
    local_epochs: int = 2
    lr: float = 0.05
    batch: int = 32
    window_slots: int = 1440  # local training window
    base_dropout: float = 0.10
    dropout_sites: list[int] = field(default_factory=list)
    dropout_sites_prob: float = 0.0
    low_quality_sites: list[int] = field(default_factory=list)
    low_quality_noise: float = 0.0  # noise on the stored training logs only (not on live counters)
    free_rider_sites: list[int] = field(default_factory=list)  # send random updates
    # Device energy model, Yang et al. (2021): kappa C D f^2 + p s / r.
    kappa: float = 1e-28
    cycles_per_sample: float = 2e4
    cpu_ghz_range: tuple[float, float] = (1.0, 2.0)
    tx_power_w: float = 0.5
    uplink_mbps_range: tuple[float, float] = (5.0, 50.0)


@dataclass
class IncentiveParams:
    # R_i = alpha Q_i - beta C_i + gamma P_i, with alpha + beta + gamma = 1.
    alpha: float = 0.5
    beta: float = 0.2
    gamma: float = 0.3
    participation_ewma: float = 0.8
    elasticity: float = 0.3  # how strongly payment raises participation (swept)
    min_participation: float = 0.05


@dataclass
class Scenario:
    name: str = "baseline"
    description: str = ""
    radio: RadioParams = field(default_factory=RadioParams)
    traffic: TrafficParams = field(default_factory=TrafficParams)
    network: NetworkParams = field(default_factory=NetworkParams)
    telemetry: TelemetryParams = field(default_factory=TelemetryParams)
    fl: FLParams = field(default_factory=FLParams)
    incentive: IncentiveParams = field(default_factory=IncentiveParams)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def digest(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, default=list).encode()
        return hashlib.sha256(blob).hexdigest()[:12]


def _merge(obj, overrides: dict):
    for key, value in overrides.items():
        if not hasattr(obj, key):
            raise KeyError(f"unknown parameter {type(obj).__name__}.{key}")
        current = getattr(obj, key)
        if dataclasses.is_dataclass(current):
            _merge(current, value)
        else:
            setattr(obj, key, tuple(value) if isinstance(current, tuple) else value)
    return obj


def make_scenario(overrides: dict | None = None) -> Scenario:
    return _merge(Scenario(), overrides or {})


def load_scenario(path: str | Path, extra: dict | None = None) -> Scenario:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    scenario = make_scenario(raw)
    if extra:
        _merge(scenario, extra)
    return scenario
