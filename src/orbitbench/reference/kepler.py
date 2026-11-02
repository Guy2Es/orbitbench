# src/orbitbench/reference/kepler.py
"""Two-body motion on an elliptic orbit: elements to state, and the state some time later (Kepler's equation)."""
import math

import numpy as np

from orbitbench.constants import EARTH_MU_KM3_S2


def _rotation(raan_deg: float, inc_deg: float, aop_deg: float) -> np.ndarray:
    """Perifocal to inertial: R3(raan) R1(inc) R3(aop)."""
    def r3(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])

    def r1(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])
    return r3(math.radians(raan_deg)) @ r1(math.radians(inc_deg)) @ r3(math.radians(aop_deg))


def mean_motion(sma_km: float, mu_km3_s2: float = EARTH_MU_KM3_S2) -> float:
    return math.sqrt(mu_km3_s2 / sma_km**3)


def solve_kepler(mean_anomaly: float, ecc: float) -> float:
    """Eccentric anomaly from the mean anomaly, by Newton's method."""
    m = math.remainder(mean_anomaly, 2.0 * math.pi)
    e_anom = m if ecc < 0.8 else math.pi
    for _ in range(100):
        step = (e_anom - ecc * math.sin(e_anom) - m) / (1.0 - ecc * math.cos(e_anom))
        e_anom -= step
        if abs(step) < 1e-15:
            break
    return e_anom


def state_from_elements(sma_km, ecc, inc_deg, raan_deg, aop_deg, ta_deg, mu_km3_s2=EARTH_MU_KM3_S2):
    """Position (km) and velocity (km/s) in the inertial frame of the elements."""
    nu = math.radians(ta_deg)
    p = sma_km * (1.0 - ecc**2)
    r = p / (1.0 + ecc * math.cos(nu))
    pos = np.array([r * math.cos(nu), r * math.sin(nu), 0.0])
    k = math.sqrt(mu_km3_s2 / p)
    vel = np.array([-k * math.sin(nu), k * (ecc + math.cos(nu)), 0.0])
    rot = _rotation(raan_deg, inc_deg, aop_deg)
    return rot @ pos, rot @ vel


def propagate(sma_km, ecc, inc_deg, raan_deg, aop_deg, ta_deg, dt_s, mu_km3_s2=EARTH_MU_KM3_S2):
    """State `dt_s` seconds after the epoch of the elements, point-mass gravity."""
    nu = math.radians(ta_deg)
    e0 = 2.0 * math.atan2(math.sqrt(1.0 - ecc) * math.sin(nu / 2.0), math.sqrt(1.0 + ecc) * math.cos(nu / 2.0))
    m = e0 - ecc * math.sin(e0) + mean_motion(sma_km, mu_km3_s2) * dt_s
    e1 = solve_kepler(m, ecc)
    nu1 = 2.0 * math.atan2(math.sqrt(1.0 + ecc) * math.sin(e1 / 2.0), math.sqrt(1.0 - ecc) * math.cos(e1 / 2.0))
    return state_from_elements(sma_km, ecc, inc_deg, raan_deg, aop_deg, math.degrees(nu1), mu_km3_s2)
