# src/orbitbench/reference/plane_change.py
"""Pure inclination change of a circular orbit, burned at a node: the velocity turns about the line of nodes."""
import math
from dataclasses import dataclass

from orbitbench.constants import EARTH_MU_KM3_S2


@dataclass(frozen=True)
class PlaneChange:
    speed_km_s: float
    delta_v_km_s: float       # norm of the burn
    along_velocity_km_s: float   # VNB components: velocity, orbit normal, bi-normal (always 0)
    along_normal_km_s: float

    @property
    def total_m_s(self) -> float:
        return self.delta_v_km_s * 1000.0


def plane_change(r_km: float, inc1_deg: float, inc2_deg: float, mu_km3_s2: float = EARTH_MU_KM3_S2) -> PlaneChange:
    """Inclination `inc1` to `inc2` on the circular orbit of radius `r_km`, burned at a node."""
    v = math.sqrt(mu_km3_s2 / r_km)
    d = math.radians(inc2_deg - inc1_deg)
    return PlaneChange(speed_km_s=v, delta_v_km_s=2.0 * v * abs(math.sin(d / 2.0)),
                       along_velocity_km_s=v * (math.cos(d) - 1.0), along_normal_km_s=v * math.sin(d))
