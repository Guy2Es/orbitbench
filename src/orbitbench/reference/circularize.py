# src/orbitbench/reference/circularize.py
"""Circularizing an elliptic Earth orbit with one burn at an apsis."""
import math
from dataclasses import dataclass

from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.reference.kepler import mean_motion


@dataclass(frozen=True)
class Circularization:
    apoapsis_dv_km_s: float        # speed to add at apoapsis to reach the circle of radius ra
    periapsis_dv_km_s: float       # speed to remove at periapsis to reach the circle of radius rp
    time_to_apoapsis_s: float      # from the given true anomaly, going forward

    @property
    def best_km_s(self) -> float:
        """Apoapsis is never beaten: among all single burns that make the orbit circular it is the cheapest."""
        return min(self.apoapsis_dv_km_s, self.periapsis_dv_km_s)

    @property
    def best_m_s(self) -> float:
        return 1000.0 * self.best_km_s


def circularize(sma_km: float, ecc: float, ta_deg: float, mu: float = EARTH_MU_KM3_S2) -> Circularization:
    ra, rp = sma_km * (1.0 + ecc), sma_km * (1.0 - ecc)
    v_apo = math.sqrt(mu * (2.0 / ra - 1.0 / sma_km))
    v_peri = math.sqrt(mu * (2.0 / rp - 1.0 / sma_km))
    nu = math.radians(ta_deg)
    e_anom = 2.0 * math.atan2(math.sqrt(1.0 - ecc) * math.sin(nu / 2.0), math.sqrt(1.0 + ecc) * math.cos(nu / 2.0))
    mean_anomaly = e_anom - ecc * math.sin(e_anom)
    wait = ((math.pi - mean_anomaly) % (2.0 * math.pi)) / mean_motion(sma_km, mu)
    return Circularization(apoapsis_dv_km_s=math.sqrt(mu / ra) - v_apo, periapsis_dv_km_s=v_peri - math.sqrt(mu / rp),
                           time_to_apoapsis_s=wait)
