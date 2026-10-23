"""Integrity tests for the closed-loop simulation: determinism, common random
numbers, no use of undelivered or future data, an equal information channel,
resource conservation, and fair baselines."""

import numpy as np
import pytest

from fndt.config import make_scenario
from fndt.environment import build_environment
from fndt.simulator import STRATEGIES, STRATEGY_BY_NAME, Run, _site_aggregates, deliver

SMALL = {"network": {"slots": 120}, "fl": {"retrain_every_slots": 60, "rounds": 2}}
LEARNED = ("centralized", "fl_only", "fl_state", "fndt_no_incentive", "fndt")


@pytest.fixture(scope="module")
def env():
    return build_environment(make_scenario(SMALL), seed=3)


def test_environment_is_deterministic(env):
    again = build_environment(make_scenario(SMALL), seed=3)
    assert np.array_equal(env.demand, again.demand)
    assert np.array_equal(env.serving, again.serving)


def test_runs_are_deterministic(env):
    a = Run(env, STRATEGY_BY_NAME["fndt"]).run()
    b = Run(env, STRATEGY_BY_NAME["fndt"]).run()
    assert a == b


def test_common_random_numbers(env):
    """Every strategy is evaluated on identical offered traffic and identical channel draws."""
    runs = [Run(env, s) for s in STRATEGIES]
    for r in runs[1:]:
        assert np.array_equal(r.load, runs[0].load)
        assert np.array_equal(r.rep_load, runs[0].rep_load)


def test_noise_factors_are_mean_one():
    sc = make_scenario({"network": {"slots": 400}, "telemetry": {"report_noise": 0.3, "unreliable_sites": [1], "unreliable_noise": 0.4}})
    e = build_environment(sc, seed=5)
    assert e.channel_noise.mean() == pytest.approx(1.0, abs=0.02)
    assert e.pipeline_noise[:, 1].mean() == pytest.approx(1.0, abs=0.03)


def _perturb_future_and_forecast(env_, name, t):
    r = Run(env_, STRATEGY_BY_NAME[name])
    cut = t - r.lag + 1  # first slot whose information has not reached the controller at decision time t
    for arr in (r.rep_load, r.raw_load, r.meas_load, r.logs, r.load, r.rep_cyc, r.raw_cyc):
        arr[cut:] *= 5.0
    if r.spec.forecaster in ("pooled", "fedavg", "fedavg_incentive"):
        r._retrain(t, 0)
    if r.holt is not None:
        for k in range(cut):
            r.holt.update(r.rep_load[k])
    return r._forecast(t)


@pytest.mark.parametrize("staleness", [0, 2])
@pytest.mark.parametrize("name", ["greedy", "greedy_sr", "centralized", "fl_only", "ndt_only", "fndt"])
def test_decisions_use_only_delivered_data(name, staleness):
    """Changing data the controller has not yet received (training and inference) must not change the forecast."""
    sc = make_scenario({**SMALL, "telemetry": {"staleness_slots": staleness}})
    e = build_environment(sc, seed=6)
    t = e.warmup + 1
    clean = Run(e, STRATEGY_BY_NAME[name])
    if clean.spec.forecaster in ("pooled", "fedavg", "fedavg_incentive"):
        clean._retrain(t, 0)
    if clean.holt is not None:
        for k in range(t - clean.lag + 1):
            clean.holt.update(clean.rep_load[k])
    before = clean._forecast(t)
    after = _perturb_future_and_forecast(e, name, t)
    assert np.allclose(before, after)


def test_federated_forecasts_pass_the_same_channel():
    """FL forecasts are corrupted and repeated exactly like load reports from the same site."""
    sc = make_scenario({**SMALL, "telemetry": {"unreliable_sites": [2], "stale_prob": 1.0, "unreliable_noise": 0.5}})
    e = build_environment(sc, seed=7)
    r = Run(e, STRATEGY_BY_NAME["fndt"])
    t = e.warmup + 1
    r._retrain(t, 0)
    first = r._forecast(t).copy()
    second = r._forecast(t + 1)
    assert second[2] == first[2]  # stale event: the controller keeps the previous message
    assert not np.isclose(second[0], first[0])


def test_centralized_avoids_aggregation_noise_but_not_pipeline_faults():
    sc = make_scenario({**SMALL, "telemetry": {"report_noise": 0.3, "unreliable_sites": [1], "unreliable_noise": 0.5}})
    e = build_environment(sc, seed=8)
    r = Run(e, STRATEGY_BY_NAME["centralized"])
    assert np.allclose(r.raw_load[:, 0], r.meas_load[:, 0])
    assert np.allclose(r.raw_load[:, 1], r.meas_load[:, 1] * e.pipeline_noise[:, 1])
    assert np.allclose(deliver(r.meas_load, e)[:, 0], r.meas_load[:, 0] * e.channel_noise[:, 0])


def test_low_quality_logs_affect_training_only():
    sc = make_scenario({**SMALL, "fl": {"low_quality_sites": [1], "low_quality_noise": 0.6}})
    e = build_environment(sc, seed=9)
    r = Run(e, STRATEGY_BY_NAME["fndt"])
    assert not np.allclose(r.logs[:, 1], r.meas_load[:, 1])
    assert np.allclose(r.rep_load[:, 1], r.meas_load[:, 1] * e.channel_noise[:, 1])


@pytest.mark.parametrize("spec", STRATEGIES, ids=lambda s: s.name)
def test_allocations_use_exactly_the_pools(env, spec):
    r = Run(env, spec, trace=True)
    r.run()
    sc = env.scenario.network
    assert np.allclose(np.sum(r.trace["alloc_mhz"], axis=1), sc.radio_pool_mhz)
    assert np.allclose(np.sum(r.trace["alloc_ghz"], axis=1), sc.mec_pool_ghz)
    assert np.all(np.array(r.trace["alloc_mhz"]) > 0)


def test_static_is_equal_split(env):
    r = Run(env, STRATEGY_BY_NAME["static"], trace=True)
    r.run()
    alloc = np.array(r.trace["alloc_mhz"])
    assert np.allclose(alloc, alloc[0, 0])


def test_mec_drops_are_counted():
    """Starving the edge pool must show up in the drop rate."""
    sc = make_scenario({**SMALL, "network": {"slots": 120, "mec_pool_ghz": 10.0}})
    e = build_environment(sc, seed=10)
    res = Run(e, STRATEGY_BY_NAME["static"]).run()
    assert res["drop_rate"] > 0.05


def test_only_centralized_exports_raw_records(env):
    shared = _site_aggregates(env)
    for spec in STRATEGIES:
        res = Run(env, spec, shared).run()
        assert (res["raw_records_exposed"] > 0) == (spec.name == "centralized")


def test_incentive_downweights_free_rider():
    sc = make_scenario({**SMALL, "network": {"slots": 180}, "fl": {"free_rider_sites": [6], "rounds": 3, "retrain_every_slots": 60}})
    env = build_environment(sc, seed=4)
    r = Run(env, STRATEGY_BY_NAME["fndt"])
    r.run()
    rewards = np.array(r.trainer.log.rewards)
    honest = np.delete(rewards, 6, axis=1)
    assert rewards[:, 6].mean() < honest.mean()


def test_twin_model_mismatch_lowers_fidelity():
    base = build_environment(make_scenario(SMALL), seed=11)
    mism = build_environment(make_scenario({**SMALL, "network": {"slots": 120, "service_scv": 3.0}}), seed=11)
    f0 = Run(base, STRATEGY_BY_NAME["fndt"]).run()["twin_fidelity"]
    f1 = Run(mism, STRATEGY_BY_NAME["fndt"]).run()["twin_fidelity"]
    assert f1 < f0
