"""Queueing and capacity-assignment models.

Each site has a radio queue and an MEC queue. Within a slot each queue is an
M/M/1 system (mean sojourn L / (mu - lambda), Kleinrock 1975) sitting on top of
a fluid backlog that carries overload from slot to slot through a Lindley-type
recursion Q' = min(max(0, Q + (lambda - mu) dt), Q_max) (Lindley, 1952).
Traffic that overflows the buffer is dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RHO_CAP = 0.98  # M/M/1 term is evaluated at most at this utilisation


@dataclass
class QueueStep:
    mean_s: np.ndarray  # mean sojourn of traffic arriving this slot, seconds
    wait_s: np.ndarray  # backlog component of the delay
    service_mean_s: np.ndarray  # M/M/1 component (exponential)
    backlog_end: np.ndarray
    dropped: np.ndarray
    served: np.ndarray
    utilisation: np.ndarray


def queue_step(lam, mu, backlog, job, dt, buffer_s) -> QueueStep:
    """Advance one slot for vectors of sites. Units: lam, mu per second; job, backlog in work units."""
    lam = np.maximum(np.asarray(lam, float), 0.0)
    mu = np.maximum(np.asarray(mu, float), 1e-9)
    q_max = buffer_s * mu
    q_raw = backlog + (lam - mu) * dt
    dropped = np.maximum(q_raw - q_max, 0.0)
    q_end = np.clip(q_raw, 0.0, q_max)
    served = lam * dt + backlog - q_end - dropped
    wait = 0.5 * (backlog + q_end) / mu
    rho = np.minimum(lam / mu, RHO_CAP)
    service = job / (mu * (1.0 - rho))
    return QueueStep(
        mean_s=wait + service,
        wait_s=wait,
        service_mean_s=service,
        backlog_end=q_end,
        dropped=dropped,
        served=served,
        utilisation=np.minimum(lam / mu, 1.0),
    )


def kleinrock(need: np.ndarray, total: float) -> np.ndarray:
    """Square-root capacity assignment minimising traffic-weighted M/M/1 delay.

    need_i is the resource each site needs just to carry its load (lambda_i / rate
    per resource unit). Kleinrock (1976): C_i = need_i + C_e sqrt(need_i) / sum sqrt(need_j),
    with excess C_e = total - sum need_j. If the network is overloaded (C_e <= 0) the
    formula has no solution, and we fall back to stabilising as many sites as possible.
    """
    need = np.maximum(np.asarray(need, float), 1e-9)
    excess = total - need.sum()
    if excess > 0:
        root = np.sqrt(need)
        return need + excess * root / root.sum()
    return protect_smallest(need, total)


def protect_smallest(need: np.ndarray, total: float, margin: float = 1.05) -> np.ndarray:
    """Overload fallback: keep the least-loaded sites stable, share the rest by demand."""
    order = np.argsort(need)
    alloc = np.zeros_like(need)
    left = total
    stable = []
    for i in order:
        if need[i] * margin <= left * 0.999:
            alloc[i] = need[i] * margin
            left -= alloc[i]
            stable.append(i)
        else:
            break
    rest = np.setdiff1d(np.arange(need.size), stable)
    if rest.size:
        alloc[rest] = left * need[rest] / need[rest].sum()
    else:
        alloc += left * need / need.sum()
    return alloc


def proportional(weight: np.ndarray, total: float) -> np.ndarray:
    weight = np.maximum(np.asarray(weight, float), 1e-9)
    return total * weight / weight.sum()


def equal(n: int, total: float) -> np.ndarray:
    return np.full(n, total / n)


def sample_sojourn(rng, wait_s, service_mean_s, n):
    """Draw n sojourn times per site: backlog wait plus an exponential M/M/1 sojourn."""
    return wait_s[:, None] + rng.exponential(1.0, (wait_s.size, n)) * service_mean_s[:, None]
