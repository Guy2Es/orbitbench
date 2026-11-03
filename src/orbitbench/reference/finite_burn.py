# src/orbitbench/reference/finite_burn.py
"""A prograde burn of finite duration from a circular orbit: the apoapsis it reaches, by integrating the thrust,
and the duration that reaches a given apoapsis. A second burn then circularizes the orbit at that apoapsis: its start
and its duration are found by integration too. The impulsive formulas are the first guess and are not the answer."""
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, minimize

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


def _fly(state, duration_s, thrust_n, mdot_kg_s, thrusting: bool):
    """The planar state [x, y, vx, vy, mass] after `duration_s` of coast or of thrust along the velocity."""
    def rhs(_, y):
        acc = -EARTH_MU_KM3_S2 * y[:2] / np.linalg.norm(y[:2]) ** 3
        if thrusting:
            acc = acc + (thrust_n / y[4] / 1000.0) * y[2:4] / np.linalg.norm(y[2:4])
        return np.concatenate([y[2:4], acc, [-mdot_kg_s if thrusting else 0.0]])

    if duration_s <= 0.0:
        return state
    return solve_ivp(rhs, (0.0, duration_s), state, method="DOP853", rtol=1e-12, atol=1e-9).y[:, -1]


def _periapsis_apoapsis(state):
    pos, vel = state[:2], state[2:4]
    r = np.linalg.norm(pos)
    sma = 1.0 / (2.0 / r - vel @ vel / EARTH_MU_KM3_S2)
    h = pos[0] * vel[1] - pos[1] * vel[0]
    ecc = np.linalg.norm(np.array([vel[1] * h, -vel[0] * h]) / EARTH_MU_KM3_S2 - pos / r)
    return float(sma * (1.0 - ecc)), float(sma * (1.0 + ecc))


def _time_to_apoapsis_s(state) -> float:
    """Coast time from `state` to the next apoapsis: the sign change of r.v, bracketed within one period."""
    pos, vel = state[:2], state[2:4]
    sma = 1.0 / (2.0 / np.linalg.norm(pos) - vel @ vel / EARTH_MU_KM3_S2)
    period = 2.0 * math.pi * math.sqrt(sma**3 / EARTH_MU_KM3_S2)
    radial = lambda t: float(np.dot(*[(_fly(state, t, 0.0, 0.0, False))[i:i + 2] for i in (0, 2)]))
    grid = np.linspace(1.0, period, 48)
    values = [radial(t) for t in grid]
    for lo, hi, a, b in zip(grid[:-1], grid[1:], values[:-1], values[1:]):
        if a > 0.0 >= b:
            return float(brentq(radial, lo, hi, xtol=1e-6))
    raise RuntimeError("no apoapsis found within a period")


def circularization(r1_km, ra_km, thrust_n, isp_s, mass_kg, first_duration_s) -> dict:
    """The second burn, which circularizes at `ra_km` after the first one of `first_duration_s`: the coast from the
    end of the first burn to the start of the second, its duration, and the worst relative miss of the final periapsis
    and apoapsis radii from `ra_km`. A burn of a thousand seconds cannot make the orbit exactly circular, so this is the
    best the pair (start, duration) can do."""
    mdot = mass_flow_kg_s(thrust_n, isp_s)
    after_first = _fly(np.array([r1_km, 0.0, 0.0, math.sqrt(EARTH_MU_KM3_S2 / r1_km), mass_kg]), first_duration_s,
                       thrust_n, mdot, True)
    sma = 1.0 / (2.0 / np.linalg.norm(after_first[:2]) - after_first[2:4] @ after_first[2:4] / EARTH_MU_KM3_S2)
    dv = math.sqrt(EARTH_MU_KM3_S2 / ra_km) - math.sqrt(EARTH_MU_KM3_S2 * (2.0 / ra_km - 1.0 / sma))
    guess = after_first[4] * (1.0 - math.exp(-dv * 1000.0 / (isp_s * GMAT_THRUSTER_G0_M_S2))) / mdot
    apoapsis_at = _time_to_apoapsis_s(after_first)

    def worst(x):
        rp, ra = _periapsis_apoapsis(_fly(_fly(after_first, x[0], thrust_n, mdot, False), x[1], thrust_n, mdot, True))
        return max(abs(rp - ra_km), abs(ra - ra_km)) / ra_km

    best = minimize(worst, [apoapsis_at - guess / 2.0, guess], method="Nelder-Mead",
                    options={"xatol": 1e-3, "fatol": 1e-9, "maxiter": 400})
    return {"coast_s": float(best.x[0]), "duration_s": float(best.x[1]), "worst_miss": float(best.fun),
            "fuel_kg": float(mdot * (first_duration_s + best.x[1]))}
