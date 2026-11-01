# src/orbitbench/reference/hohmann.py
"""Two-impulse Hohmann transfer between circular coplanar orbits, from the vis-viva equation."""
import math
from dataclasses import dataclass

from orbitbench.constants import EARTH_MU_KM3_S2


@dataclass(frozen=True)
class Hohmann:
    transfer_sma_km: float
    delta_v1_km_s: float   # signed, along the velocity at the start orbit
    delta_v2_km_s: float   # signed, along the velocity at the transfer apoapsis (or periapsis)
    transfer_time_s: float

    @property
    def total_km_s(self) -> float:
        return abs(self.delta_v1_km_s) + abs(self.delta_v2_km_s)

    @property
    def total_m_s(self) -> float:
        return self.total_km_s * 1000.0


def hohmann(r1_km: float, r2_km: float, mu_km3_s2: float = EARTH_MU_KM3_S2) -> Hohmann:
    a = (r1_km + r2_km) / 2.0
    v_start = math.sqrt(mu_km3_s2 / r1_km)
    v_end = math.sqrt(mu_km3_s2 / r2_km)
    v_transfer_start = math.sqrt(mu_km3_s2 * (2.0 / r1_km - 1.0 / a))
    v_transfer_end = math.sqrt(mu_km3_s2 * (2.0 / r2_km - 1.0 / a))
    return Hohmann(
        transfer_sma_km=a,
        delta_v1_km_s=v_transfer_start - v_start,
        delta_v2_km_s=v_end - v_transfer_end,
        transfer_time_s=math.pi * math.sqrt(a**3 / mu_km3_s2),
    )
