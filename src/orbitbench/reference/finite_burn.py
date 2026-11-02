# src/orbitbench/reference/finite_burn.py
"""A prograde burn of finite duration from a circular orbit: the apoapsis it reaches, by integrating the thrust,
and the duration that reaches a given apoapsis. The impulsive formula is the first guess and is not the answer."""
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from orbitbench.constants import EARTH_MU_KM3_S2

GMAT_THRUSTER_G0_M_S2 = 9.81     # the g0 GMAT's thrusters burn propellant with


def mass_flow_kg_s(thrust_n: float, isp_s: float) -> float:
    return thrust_n / (isp_s * GMAT_THRUSTER_G0_M_S2)


def impulsive_duration_s(r1_km, ra_km, thrust_n, isp_s, mass_kg) -> float:
    """Burn time of the impulsive Hohmann first burn, by Tsiolkovsky: where the finite burn starts being corrected."""
    a = (r1_km + ra_km) / 2.0
    dv = math.sqrt(EARTH_MU_KM3_S2 * (2.0 / r1_km - 1.0 / a)) - math.sqrt(EARTH_MU_KM3_S2 / r1_km)
    return mass_kg * (1.0 - math.exp(-dv * 1000.0 / (isp_s * GMAT_THRUSTER_G0_M_S2))) / mass_flow_kg_s(thrust_n, isp_s)


def apoapsis_after(r1_km, thrust_n, isp_s, mass_kg, duration_s) -> float:
    """Apoapsis radius (km) after `duration_s` of thrust along the velocity from the circular orbit of radius r1_km.
    Where on the orbit the burn starts does not matter: the orbit is circular and the problem is rotation-symmetric."""
    speed = math.sqrt(EARTH_MU_KM3_S2 / r1_km)
    mdot = mass_flow_kg_s(thrust_n, isp_s)

    def rhs(_, y):
        r = np.linalg.norm(y[:2])
        acc = -EARTH_MU_KM3_S2 * y[:2] / r**3 + (thrust_n / y[4] / 1000.0) * y[2:4] / np.linalg.norm(y[2:4])
        return np.concatenate([y[2:4], acc, [-mdot]])

    y = solve_ivp(rhs, (0.0, duration_s), np.array([r1_km, 0.0, 0.0, speed, mass_kg]), method="DOP853",
                  rtol=1e-12, atol=1e-9).y[:, -1]
    pos, vel = y[:2], y[2:4]
    r = np.linalg.norm(pos)
    sma = 1.0 / (2.0 / r - vel @ vel / EARTH_MU_KM3_S2)
    h = pos[0] * vel[1] - pos[1] * vel[0]
    ecc = np.linalg.norm(np.array([vel[1] * h, -vel[0] * h]) / EARTH_MU_KM3_S2 - pos / r)
    return float(sma * (1.0 + ecc))


def duration_for_apoapsis(r1_km, ra_km, thrust_n, isp_s, mass_kg, max_s: float) -> float:
    """The burn duration that reaches `ra_km`, found by bracketing between a second and `max_s`."""
    return float(brentq(lambda d: apoapsis_after(r1_km, thrust_n, isp_s, mass_kg, d) - ra_km, 1.0, max_s,
                        xtol=1e-6))
