# src/orbitbench/reference/tsiolkovsky.py
"""The rocket equation and the escape burn from a circular orbit, in closed form."""
import math

G0_M_S2 = 9.80665


def propellant_kg(mass_kg: float, delta_v_m_s: float, isp_s: float) -> float:
    """Propellant burned to give `mass_kg` (initial mass, propellant included) a delta-v: m0 (1 - exp(-dv / (Isp g0)))."""
    return mass_kg * (1.0 - math.exp(-delta_v_m_s / (isp_s * G0_M_S2)))


def escape_delta_v_m_s(radius_km: float, mu_km3_s2: float) -> float:
    """The one impulse along the velocity that takes a circular orbit of this radius to escape speed: (sqrt 2 - 1) v_circ."""
    return (math.sqrt(2.0) - 1.0) * math.sqrt(mu_km3_s2 / radius_km) * 1000.0
