# src/orbitbench/reference/plane_change_budget.py
"""Hohmann transfer between circular orbits with a plane change shared between its two burns, and the rocket equation."""
import math
from dataclasses import dataclass

from scipy.optimize import minimize_scalar

from orbitbench.constants import EARTH_MU_KM3_S2

G0_M_S2 = 9.80665


@dataclass(frozen=True)
class SplitTransfer:
    r1_km: float
    r2_km: float
    plane_change_deg: float
    first_burn_angle_deg: float   # part of the plane change made at the first burn (at the start orbit)
    transfer_time_s: float
    # Burns in VNB, km/s: [along the velocity, along the orbit normal]. The second burn is at the opposite node,
    # where a positive normal component lowers the inclination, so its sign is the opposite one.
    burn1_km_s: tuple
    burn2_km_s: tuple

    @property
    def total_km_s(self) -> float:
        return math.hypot(*self.burn1_km_s) + math.hypot(*self.burn2_km_s)

    @property
    def total_m_s(self) -> float:
        return self.total_km_s * 1000.0


def _speeds(r1_km: float, r2_km: float, mu: float) -> tuple:
    a = (r1_km + r2_km) / 2.0
    return (math.sqrt(mu / r1_km), math.sqrt(mu / r2_km),
            math.sqrt(mu * (2.0 / r1_km - 1.0 / a)), math.sqrt(mu * (2.0 / r2_km - 1.0 / a)), a)


def split_transfer(r1_km: float, r2_km: float, plane_change_deg: float, first_burn_angle_deg: float,
                   mu_km3_s2: float = EARTH_MU_KM3_S2) -> SplitTransfer:
    """Both burns at the nodes; the plane rotates by the first-burn angle, then by the rest, about the line of nodes."""
    v1, v2, vt1, vt2, a = _speeds(r1_km, r2_km, mu_km3_s2)
    alpha = math.radians(first_burn_angle_deg)
    beta = math.radians(plane_change_deg) - alpha
    return SplitTransfer(
        r1_km=r1_km, r2_km=r2_km, plane_change_deg=plane_change_deg, first_burn_angle_deg=first_burn_angle_deg,
        transfer_time_s=math.pi * math.sqrt(a**3 / mu_km3_s2),
        burn1_km_s=(vt1 * math.cos(alpha) - v1, vt1 * math.sin(alpha)),
        burn2_km_s=(v2 * math.cos(beta) - vt2, -v2 * math.sin(beta)))


def best_split(r1_km: float, r2_km: float, plane_change_deg: float, mu_km3_s2: float = EARTH_MU_KM3_S2) -> SplitTransfer:
    """The share of the plane change at the first burn that minimises the total delta-v."""
    def total(angle_deg):
        return split_transfer(r1_km, r2_km, plane_change_deg, angle_deg, mu_km3_s2).total_km_s
    found = minimize_scalar(total, bounds=(0.0, plane_change_deg), method="bounded", options={"xatol": 1e-10})
    return split_transfer(r1_km, r2_km, plane_change_deg, float(found.x), mu_km3_s2)


def separate_plane_change_m_s(r1_km: float, r2_km: float, plane_change_deg: float,
                              mu_km3_s2: float = EARTH_MU_KM3_S2) -> float:
    """Hohmann in the plane, then a pure plane change on the final circular orbit."""
    v1, v2, vt1, vt2, _ = _speeds(r1_km, r2_km, mu_km3_s2)
    rotation = 2.0 * v2 * math.sin(math.radians(plane_change_deg) / 2.0)
    return 1000.0 * (abs(vt1 - v1) + abs(v2 - vt2) + rotation)


def rocket_delta_v_m_s(initial_mass_kg: float, fuel_mass_kg: float, isp_s: float) -> float:
    """Tsiolkovsky: the delta-v that burning the fuel gives."""
    return isp_s * G0_M_S2 * math.log(initial_mass_kg / (initial_mass_kg - fuel_mass_kg))
