"""Integrity tests for the closed-loop simulation: determinism, common random
numbers, no use of future data, resource conservation, and fair baselines."""

import numpy as np
import pytest

from fndt.config import make_scenario
from fndt.environment import build_environment
from fndt.simulator import STRATEGIES, STRATEGY_BY_NAME, Run, _site_aggregates

SMALL = {"network": {"slots": 120}, "fl": {"retrain_every_slots": 60, "rounds": 2}}


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
    """Every strategy is evaluated on identical offered traffic."""
    runs = [Run(env, s) for s in STRATEGIES]
    for r in runs[1:]:
        assert np.array_equal(r.load, runs[0].load)
        assert np.array_equal(r.rep_load, runs[0].rep_load)


@pytest.mark.parametrize("name", ["greedy", "centralized", "fl_only", "ndt_only", "fndt"])
def test_forecast_uses_no_future_data(env, name):
    """Perturbing data at or after slot t must not change the decision input for slot t."""
    r = Run(env, STRATEGY_BY_NAME[name])
    t = env.warmup + 1
    r._retrain(t, 0) if r.spec.forecaster in ("pooled", "fedavg", "fedavg_incentive") else None
    if r.holt is not None:
        for k in range(t - r.lag + 1):
            r.holt.update(r.rep_load[k])
    before = r._forecast(t).copy()
    lag = r.lag
    for arr in (r.rep_load, r.local_load, r.load):
        arr[t - lag + 1 :] *= 5.0
    after = r._forecast(t)
    assert np.allclose(before, after)


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
