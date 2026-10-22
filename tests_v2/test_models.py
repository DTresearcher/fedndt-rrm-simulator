"""Verification tests: each checks a model component against its published formula or a known property."""

import numpy as np
import pytest

from fndt.config import RadioParams, make_scenario
from fndt.forecasting import local_sgd
from fndt.queueing import kleinrock, protect_smallest, queue_step
from fndt.radio import hex_sites, spectral_efficiency, uma_los_db, uma_nlos_db
from fndt.simulator import hypoexp_tail

P = RadioParams()


def test_hex_layout_isd():
    xy = hex_sites(7, 500.0)
    d = np.linalg.norm(xy[1:] - xy[0], axis=1)
    assert np.allclose(d, 500.0)


def test_uma_los_pl1_matches_38901():
    d2d = np.array([100.0])
    d3d = np.sqrt(100.0**2 + 23.5**2)
    expected = 28.0 + 22 * np.log10(d3d) + 20 * np.log10(4.0)
    assert uma_los_db(d2d, P)[0] == pytest.approx(expected)


def test_uma_nlos_is_max_of_los_and_nlos_prime():
    d2d = np.array([50.0, 300.0, 1000.0])
    d3d = np.sqrt(d2d**2 + 23.5**2)
    nlos_prime = 13.54 + 39.08 * np.log10(d3d) + 20 * np.log10(4.0)
    assert np.allclose(uma_nlos_db(d2d, P), np.maximum(uma_los_db(d2d, P), nlos_prime))


def test_shannon_bound_36942():
    se = spectral_efficiency(np.array([-11.0, 0.0, 40.0]), P)
    assert se[0] == 0.0
    assert se[1] == pytest.approx(0.6 * np.log2(2.0))
    assert se[2] == pytest.approx(4.4)


def _mm1_cost(alloc, need):
    return np.sum(need / (alloc - need))


def test_kleinrock_is_optimal_and_feasible():
    rng = np.random.default_rng(0)
    for _ in range(20):
        need = rng.uniform(1, 10, 6)
        total = need.sum() * 1.5
        k = kleinrock(need, total)
        assert k.sum() == pytest.approx(total)
        best = _mm1_cost(k, need)
        for _ in range(200):
            x = need + rng.dirichlet(np.ones(6)) * (total - need.sum())
            assert _mm1_cost(x, need) >= best - 1e-9


def test_overload_fallback_uses_whole_pool():
    need = np.array([5.0, 6.0, 30.0])
    alloc = protect_smallest(need, 35.0)
    assert alloc.sum() == pytest.approx(35.0)
    assert alloc[0] >= need[0] and alloc[1] >= need[1]


def test_queue_conservation_and_mm1_mean():
    lam, mu = np.array([5.0, 12.0]), np.array([10.0, 10.0])
    backlog = np.array([0.0, 3.0])
    st = queue_step(lam, mu, backlog, job=1.0, dt=60.0, buffer_s=2.0)
    # offered + initial backlog = served + dropped + final backlog
    assert np.allclose(lam * 60 + backlog, st.served + st.dropped + st.backlog_end)
    assert st.mean_s[0] == pytest.approx(1.0 / (10.0 - 5.0))  # M/M/1 sojourn L/(mu-lambda)
    assert st.backlog_end[1] == pytest.approx(20.0)  # buffer cap = 2 s of service
    assert st.dropped[1] > 0


def test_hypoexponential_tail_matches_monte_carlo():
    rng = np.random.default_rng(1)
    m1, m2, x = 0.02, 0.01, 0.05
    sample = rng.exponential(m1, 400_000) + rng.exponential(m2, 400_000)
    assert hypoexp_tail(np.array(x), np.array(m1), np.array(m2)) == pytest.approx((sample > x).mean(), abs=2e-3)


def test_fedavg_one_full_batch_step_equals_central_gradient_step():
    rng = np.random.default_rng(2)
    w0 = rng.normal(size=4)
    parts = [(rng.normal(size=(50, 4)), rng.normal(size=50)) for _ in range(3)]
    lr = 0.01
    local = [local_sgd(w0, X, y, epochs=1, lr=lr, batch=50, rng=rng) for X, y in parts]
    fedavg = np.mean(local, axis=0)  # equal sample counts
    X = np.vstack([p[0] for p in parts])
    y = np.concatenate([p[1] for p in parts])
    central = w0 - lr * 2 * X.T @ (X @ w0 - y) / len(y)
    assert np.allclose(fedavg, central)


def test_scenario_override_rejects_unknown_keys():
    with pytest.raises(KeyError):
        make_scenario({"traffic": {"no_such_field": 1}})
