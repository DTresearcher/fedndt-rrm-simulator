"""Demand forecasting: a linear autoregressive model (trained centrally or by FedAvg)
and Holt's linear exponential smoothing (the non-learned twin predictor).

The forecast for slot tau may only use data up to slot tau - 1 - staleness.
tests_v2/test_no_leakage.py checks this by perturbing future data.
"""

from __future__ import annotations

import numpy as np

FEATURE_DIM = 9


def features(z: np.ndarray, hours: np.ndarray, tau: np.ndarray, lag: int, day_slots: int) -> np.ndarray:
    """Feature rows for target slots tau of one site's normalised series z.

    Uses only z[: tau - lag], i.e. the last observation available is a = tau - lag.
    """
    a = tau - lag
    recent = np.stack([z[a - k] for k in range(12)], axis=1)
    hour = hours[tau]
    return np.column_stack(
        [
            np.ones(tau.size),
            z[a],
            z[a - 1],
            z[a - 2],
            z[a - 5],
            z[tau - day_slots],  # same time yesterday
            recent.mean(axis=1),
            np.sin(2 * np.pi * hour / 24.0),
            np.cos(2 * np.pi * hour / 24.0),
        ]
    )


def site_scale(series: np.ndarray, end: int, window: int) -> float:
    """Local normalisation constant: mean demand over the site's own recent window."""
    seg = series[max(0, end - window) : end]
    return float(max(seg.mean(), 1e-6))


def training_set(series, hours, end, window, lag, day_slots):
    """Samples (X, y) for one site using targets tau in [end - window, end)."""
    scale = site_scale(series, end, window)
    z = series / scale
    first = max(end - window, day_slots + 12 + lag)
    tau = np.arange(first, end)
    if tau.size == 0:
        return np.empty((0, FEATURE_DIM)), np.empty(0), scale
    return features(z, hours, tau, lag, day_slots), z[tau], scale


def ridge_fit(X: np.ndarray, y: np.ndarray, reg: float = 1e-2) -> np.ndarray:
    A = X.T @ X + reg * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ y)


def mse(w: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
    r = X @ w - y
    return float(np.mean(r * r)) if r.size else 0.0


def local_sgd(w, X, y, epochs, lr, batch, rng) -> np.ndarray:
    """Plain minibatch SGD on squared error, as each FedAvg client does (McMahan et al., 2017)."""
    w = w.copy()
    n = len(y)
    if n == 0:
        return w
    for _ in range(epochs):
        order = rng.permutation(n)
        for start in range(0, n, batch):
            idx = order[start : start + batch]
            grad = 2.0 * X[idx].T @ (X[idx] @ w - y[idx]) / idx.size
            w -= lr * grad
    return w


def predict_site(w, series, hours, tau, lag, day_slots, window) -> float:
    scale = site_scale(series, tau - lag + 1, window)
    z = series / scale
    x = features(z, hours, np.array([tau]), lag, day_slots)[0]
    return float(max(x @ w, 0.0) * scale)


class Holt:
    """Holt's linear exponential smoothing, updated with each report as it arrives."""

    def __init__(self, n: int, level_alpha: float = 0.5, trend_beta: float = 0.05):
        self.a, self.b = level_alpha, trend_beta
        self.level = np.full(n, np.nan)
        self.trend = np.zeros(n)

    def update(self, y: np.ndarray) -> None:
        fresh = np.isnan(self.level)
        self.level[fresh] = y[fresh]
        prev = self.level.copy()
        self.level = self.a * y + (1 - self.a) * (self.level + self.trend)
        self.trend = self.b * (self.level - prev) + (1 - self.b) * self.trend

    def forecast(self, steps: int) -> np.ndarray:
        return np.maximum(self.level + steps * self.trend, 0.0)
