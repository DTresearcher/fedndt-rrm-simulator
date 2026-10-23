"""Radio model: 3GPP TR 38.901 UMa path loss and the TR 36.942 Shannon bound."""

from __future__ import annotations

import numpy as np

from fndt.config import RadioParams

C_LIGHT = 3.0e8


def hex_sites(n_sites: int, isd_m: float) -> np.ndarray:
    """Site coordinates: centre site plus hexagonal rings (TR 38.901 Table 7.2-1 layout)."""
    coords = [(0.0, 0.0)]
    ring = 1
    while len(coords) < n_sites:
        for k in range(6):
            angle = np.pi / 3 * k + np.pi / 6
            corner = np.array([np.cos(angle), np.sin(angle)]) * isd_m * ring
            step_angle = angle + 2 * np.pi / 3
            step = np.array([np.cos(step_angle), np.sin(step_angle)]) * isd_m
            for j in range(ring):
                coords.append(tuple(corner + j * step))
        ring += 1
    return np.array(coords[:n_sites])


def uma_los_db(d2d: np.ndarray, p: RadioParams) -> np.ndarray:
    """UMa LOS path loss, TR 38.901 Table 7.4.1-1 (h_E = 1 m for pedestrian UEs)."""
    fc = p.carrier_ghz
    d3d = np.sqrt(d2d**2 + (p.h_bs_m - p.h_ut_m) ** 2)
    d_bp = 4 * (p.h_bs_m - 1.0) * (p.h_ut_m - 1.0) * fc * 1e9 / C_LIGHT
    pl1 = 28.0 + 22.0 * np.log10(d3d) + 20.0 * np.log10(fc)
    pl2 = (
        28.0
        + 40.0 * np.log10(d3d)
        + 20.0 * np.log10(fc)
        - 9.0 * np.log10(d_bp**2 + (p.h_bs_m - p.h_ut_m) ** 2)
    )
    return np.where(d2d <= d_bp, pl1, pl2)


def uma_nlos_db(d2d: np.ndarray, p: RadioParams) -> np.ndarray:
    """UMa NLOS path loss: max(PL_LOS, PL'_NLOS), TR 38.901 Table 7.4.1-1.

    All links are treated as NLOS, a conservative choice that avoids the LOS
    probability model.
    """
    d2d = np.maximum(d2d, 10.0)
    d3d = np.sqrt(d2d**2 + (p.h_bs_m - p.h_ut_m) ** 2)
    nlos = (
        13.54
        + 39.08 * np.log10(d3d)
        + 20.0 * np.log10(p.carrier_ghz)
        - 0.6 * (p.h_ut_m - 1.5)
    )
    return np.maximum(uma_los_db(d2d, p), nlos)


def spectral_efficiency(sinr_db: np.ndarray, p: RadioParams) -> np.ndarray:
    """Attenuated and truncated Shannon bound, TR 36.942 Annex A.1 (bps/Hz)."""
    sinr = 10.0 ** (sinr_db / 10.0)
    se = np.minimum(p.shannon_alpha * np.log2(1.0 + sinr), p.se_max)
    return np.where(sinr_db < p.snr_min_db, 0.0, se)


def sinr_db(
    rx_serving_dbm: np.ndarray,
    rx_all_dbm: np.ndarray,
    serving: np.ndarray,
    neighbour_activity: np.ndarray,
    p: RadioParams,
) -> np.ndarray:
    """Per-user SINR with load-weighted inter-site interference.

    rx_all_dbm has shape (users, sites); neighbour_activity (sites,) in [0, 1]
    scales each interferer by its utilisation in the previous slot.
    """
    rx_lin = 10.0 ** (rx_all_dbm / 10.0)
    act = np.broadcast_to(neighbour_activity, rx_lin.shape).copy()
    act[np.arange(len(serving)), serving] = 0.0
    interference = (rx_lin * act).sum(axis=1)
    noise = 10.0 ** (p.noise_dbm_per_mhz / 10.0)
    return rx_serving_dbm - 10.0 * np.log10(noise + interference)
