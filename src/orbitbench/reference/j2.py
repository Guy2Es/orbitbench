# src/orbitbench/reference/j2.py
"""An orbit under point-mass plus J2 gravity, integrated numerically, and the elements read from its state."""
import math

import numpy as np
from scipy.integrate import solve_ivp

from orbitbench.constants import EARTH_J2, EARTH_MU_KM3_S2, EARTH_RADIUS_KM
from orbitbench.reference.kepler import state_from_elements


def acceleration(pos, mu=EARTH_MU_KM3_S2, j2=EARTH_J2, radius=EARTH_RADIUS_KM):
    """Point mass plus the J2 zonal term, the Earth's axis being z of the inertial frame."""
    x, y, z = pos
    r2 = x * x + y * y + z * z
    r = math.sqrt(r2)
    c = 1.5 * j2 * (radius / r) ** 2
    s = 5.0 * z * z / r2
    return -mu / r**3 * np.array([x * (1.0 + c * (1.0 - s)), y * (1.0 + c * (1.0 - s)), z * (1.0 + c * (3.0 - s))])


def elements_from_state(pos, vel, mu=EARTH_MU_KM3_S2) -> dict:
    """Osculating sma, ecc, inc, raan and aop (degrees in [0, 360)) of a state."""
    pos, vel = np.asarray(pos, float), np.asarray(vel, float)
    r, h = np.linalg.norm(pos), np.cross(pos, vel)
    ecc_vec = np.cross(vel, h) / mu - pos / r
    node = np.array([-h[1], h[0], 0.0])
    aop = math.atan2(np.dot(np.cross(node, ecc_vec), h) / np.linalg.norm(h), np.dot(node, ecc_vec))
    return {"sma_km": float(1.0 / (2.0 / r - vel @ vel / mu)), "ecc": float(np.linalg.norm(ecc_vec)),
            "inc_deg": math.degrees(math.acos(h[2] / np.linalg.norm(h))),
            "raan_deg": math.degrees(math.atan2(h[0], -h[1])) % 360.0, "aop_deg": math.degrees(aop) % 360.0}


def propagate_j2(sma_km, ecc, inc_deg, raan_deg, aop_deg, ta_deg, dt_s) -> tuple:
    """Position and velocity `dt_s` after the elements, by a Dormand-Prince 8(5,3) integration."""
    pos0, vel0 = state_from_elements(sma_km, ecc, inc_deg, raan_deg, aop_deg, ta_deg)

    def rhs(_, y):
        return np.concatenate([y[3:], acceleration(y[:3])])

    sol = solve_ivp(rhs, (0.0, dt_s), np.concatenate([pos0, vel0]), method="DOP853", rtol=1e-13, atol=1e-10)
    return sol.y[:3, -1], sol.y[3:, -1]
