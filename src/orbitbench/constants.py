# src/orbitbench/constants.py
"""Constants every statement, reference and replay share. Each statement states the ones it relies on."""

import math

EARTH_MU_KM3_S2 = 398600.4415   # identical to GMAT's JGM3.cof
EARTH_RADIUS_KM = 6378.1363     # the reference radius of JGM3.cof, not core.astro's 6378.137
EARTH_J2 = 4.84165374886470e-04 * math.sqrt(5.0)   # JGM3.cof stores the normalized C(2,0)
SUN_RATE_DEG_DAY = 360.0 / 365.2421897   # one turn of the node per tropical year
DEFAULT_EPOCH = "01 Jan 2026 00:00:00.000"
SATELLITE = "Sat"

# The propagator the replay imposes: the agent never chooses it.
INTEGRATOR = "PrinceDormand78"
ACCURACY = 1e-12
