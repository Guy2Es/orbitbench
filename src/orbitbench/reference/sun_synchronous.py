# src/orbitbench/reference/sun_synchronous.py
"""The inclination that makes the node of an Earth orbit drift with the Sun, two independent ways:
the secular formula of J2, and a numerical search on the drift an integration measures."""
import math

from scipy.optimize import brentq

from orbitbench.constants import EARTH_J2, EARTH_MU_KM3_S2, EARTH_RADIUS_KM, SUN_RATE_DEG_DAY
from orbitbench.reference.j2 import elements_from_state, propagate_j2

DAY_S = 86400.0


def orbit_period_s(sma_km: float) -> float:
    return 2.0 * math.pi * math.sqrt(sma_km**3 / EARTH_MU_KM3_S2)


def secular_drift_deg_day(sma_km: float, ecc: float, inc_deg: float) -> float:
    """Mean node drift of the J2 secular theory: -3/2 J2 (R/p)^2 n cos(i)."""
    n = math.sqrt(EARTH_MU_KM3_S2 / sma_km**3)
    p = sma_km * (1.0 - ecc**2)
    rate = -1.5 * EARTH_J2 * (EARTH_RADIUS_KM / p) ** 2 * n * math.cos(math.radians(inc_deg))
    return math.degrees(rate) * DAY_S


def inclination_formula(sma_km: float, ecc: float) -> float:
    """Inclination (degrees) whose secular node drift is the Sun's, from the closed form."""
    n = math.sqrt(EARTH_MU_KM3_S2 / sma_km**3)
    p = sma_km * (1.0 - ecc**2)
    cos_i = -math.radians(SUN_RATE_DEG_DAY) / DAY_S / (1.5 * EARTH_J2 * (EARTH_RADIUS_KM / p) ** 2 * n)
    if abs(cos_i) > 1.0:
        raise ValueError(f"no sun-synchronous orbit at sma={sma_km} km, ecc={ecc}")
    return math.degrees(math.acos(cos_i))


def measured_drift_deg_day(sma_km, ecc, inc_deg, raan_deg, aop_deg, ta_deg, n_orbits: int) -> float:
    """Node drift an integration of point mass plus J2 measures over `n_orbits` Keplerian periods."""
    dt = n_orbits * orbit_period_s(sma_km)
    pos, vel = propagate_j2(sma_km, ecc, inc_deg, raan_deg, aop_deg, ta_deg, dt)
    raan = elements_from_state(pos, vel)["raan_deg"]
    return math.remainder(raan - raan_deg, 360.0) / (dt / DAY_S)


def inclination_numeric(sma_km, ecc, raan_deg, aop_deg, ta_deg, n_orbits: int) -> float:
    """Inclination (degrees) whose measured drift is the Sun's, found by bracketing between 90 and 135 degrees."""
    def gap(inc_deg):
        return measured_drift_deg_day(sma_km, ecc, inc_deg, raan_deg, aop_deg, ta_deg, n_orbits) - SUN_RATE_DEG_DAY

    return float(brentq(gap, 90.0, 135.0, xtol=1e-9))

