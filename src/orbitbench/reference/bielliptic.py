# src/orbitbench/reference/bielliptic.py
"""Bi-elliptic transfer between two coplanar circular orbits, and the best intermediate apoapsis under a bound."""
import math
from dataclasses import dataclass

import numpy as np

from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.reference.hohmann import hohmann


@dataclass(frozen=True)
class Bielliptic:
    ra_km: float
    delta_v1_km_s: float           # at r1, prograde
    delta_v2_km_s: float           # at the intermediate apoapsis, signed along the velocity
    delta_v3_km_s: float           # at r2, retrograde
    time_to_second_burn_s: float
    time_to_third_burn_s: float

    @property
    def total_km_s(self) -> float:
        return abs(self.delta_v1_km_s) + abs(self.delta_v2_km_s) + abs(self.delta_v3_km_s)

    @property
    def total_m_s(self) -> float:
        return 1000.0 * self.total_km_s


def _speed(r_km: float, sma_km: float, mu: float) -> float:
    return math.sqrt(mu * (2.0 / r_km - 1.0 / sma_km))


def bielliptic(r1_km: float, r2_km: float, ra_km: float, mu: float = EARTH_MU_KM3_S2) -> Bielliptic:
    """Burn at r1 up to apoapsis ra, burn at ra to raise the periapsis to r2, burn at r2 to circularize."""
    a1, a2 = (r1_km + ra_km) / 2.0, (ra_km + r2_km) / 2.0
    dv1 = _speed(r1_km, a1, mu) - math.sqrt(mu / r1_km)
    dv2 = _speed(ra_km, a2, mu) - _speed(ra_km, a1, mu)
    dv3 = math.sqrt(mu / r2_km) - _speed(r2_km, a2, mu)
    t1 = math.pi * math.sqrt(a1**3 / mu)
    return Bielliptic(ra_km, dv1, dv2, dv3, t1, t1 + math.pi * math.sqrt(a2**3 / mu))


def best_bielliptic(r1_km: float, r2_km: float, ra_max_km: float, mu: float = EARTH_MU_KM3_S2) -> Bielliptic:
    """The cheapest bi-elliptic transfer whose intermediate apoapsis lies in [r2, ra_max]: a scan, then a refinement."""
    grid = np.geomspace(r2_km, ra_max_km, 4001)
    totals = [bielliptic(r1_km, r2_km, ra, mu).total_km_s for ra in grid]
    i = int(np.argmin(totals))
    lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
    for _ in range(100):   # golden-section refinement of the bracket
        m1, m2 = hi - (hi - lo) / 1.618033988749895, lo + (hi - lo) / 1.618033988749895
        if bielliptic(r1_km, r2_km, m1, mu).total_km_s < bielliptic(r1_km, r2_km, m2, mu).total_km_s:
            hi = m2
        else:
            lo = m1
    return bielliptic(r1_km, r2_km, (lo + hi) / 2.0, mu)


def best_transfer_m_s(r1_km: float, r2_km: float, ra_max_km: float) -> tuple:
    """(Hohmann total, best bi-elliptic total), both in m/s."""
    return hohmann(r1_km, r2_km).total_m_s, best_bielliptic(r1_km, r2_km, ra_max_km).total_m_s
