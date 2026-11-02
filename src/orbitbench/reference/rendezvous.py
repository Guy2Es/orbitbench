# src/orbitbench/reference/rendezvous.py
"""Phasing on a circular orbit: the chaser leaves a point of the orbit onto a phasing orbit and comes back to the same
point after k revolutions, when the target has just arrived there. Two references: the closed form, and the miss of a
plan measured by integrating the chaser."""
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.integrate import solve_ivp

from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.reference.kepler import propagate, state_from_elements

MAX_REVOLUTIONS = 6


def circular_period_s(radius_km: float) -> float:
    return 2.0 * math.pi * math.sqrt(radius_km**3 / EARTH_MU_KM3_S2)


def transfer_time_s(radius_km: float, phase_deg: float, revolutions: int) -> float:
    """Time for `revolutions` turns of the chaser to bring it where the target, `phase_deg` ahead, will be."""
    return circular_period_s(radius_km) * (revolutions - phase_deg / 360.0)


@dataclass(frozen=True)
class Phasing:
    revolutions: int
    period_s: float
    sma_km: float
    burn_km_s: float                # the first burn, along the velocity (negative: slowing down); the second is opposite
    low_radius_km: float            # the lowest radius of the phasing orbit

    @property
    def total_m_s(self) -> float:
        return 2000.0 * abs(self.burn_km_s)


def phasing(radius_km: float, duration_s: float, revolutions: int) -> Phasing:
    """The two-burn phasing that takes `duration_s` and `revolutions` turns of the phasing orbit."""
    period = duration_s / revolutions
    sma = (EARTH_MU_KM3_S2 * (period / (2.0 * math.pi)) ** 2) ** (1.0 / 3.0)
    energy = 2.0 / radius_km - 1.0 / sma
    if energy <= 0.0:       # an orbit of that period cannot pass through the burn point
        return Phasing(revolutions, period, sma, math.inf, -math.inf)
    speed = math.sqrt(EARTH_MU_KM3_S2 * energy)
    return Phasing(revolutions, period, sma, speed - math.sqrt(EARTH_MU_KM3_S2 / radius_km),
                   min(radius_km, 2.0 * sma - radius_km))


def best_phasing(radius_km: float, duration_s: float, min_radius_km: float) -> Optional[Phasing]:
    """The cheapest phasing whose orbit stays above `min_radius_km`, over the numbers of revolutions that fit."""
    options = [phasing(radius_km, duration_s, k) for k in range(1, MAX_REVOLUTIONS + 1)]
    options = [o for o in options if o.low_radius_km >= min_radius_km]
    return min(options, key=lambda o: o.total_m_s) if options else None


def target_state(radius_km, inc_deg, raan_deg, ta_deg, dt_s) -> tuple:
    """Position and velocity of the target on its circular orbit `dt_s` after the epoch."""
    return propagate(radius_km, 0.0, inc_deg, raan_deg, 0.0, ta_deg, dt_s)


def plan_miss(radius_km, inc_deg, raan_deg, chaser_ta_deg, target_ta_deg, burns, duration_s) -> tuple:
    """Distance (km) and relative speed (m/s) between a chaser flown through `burns` and the target, at `duration_s`.

    `burns` is a list of (time since the epoch in s, delta-v along the velocity in km/s), in chronological order.
    The chaser is integrated as a point-mass orbit with DOP853, independently of the closed form."""
    pos, vel = state_from_elements(radius_km, 0.0, inc_deg, raan_deg, 0.0, chaser_ta_deg)
    state, now = np.concatenate([pos, vel]), 0.0

    def rhs(_, y):
        r = np.linalg.norm(y[:3])
        return np.concatenate([y[3:], -EARTH_MU_KM3_S2 * y[:3] / r**3])

    for when, dv in list(burns) + [(duration_s, 0.0)]:
        if when > now:
            state = solve_ivp(rhs, (now, when), state, method="DOP853", rtol=1e-13, atol=1e-10).y[:, -1]
            now = when
        state[3:] = state[3:] + dv * state[3:] / np.linalg.norm(state[3:])
    target_pos, target_vel = target_state(radius_km, inc_deg, raan_deg, target_ta_deg, duration_s)
    return float(np.linalg.norm(state[:3] - target_pos)), 1000.0 * float(np.linalg.norm(state[3:] - target_vel))
