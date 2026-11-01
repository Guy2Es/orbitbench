# src/orbitbench/constants.py
"""Constants every statement, reference and replay share. Each statement states the ones it relies on."""

EARTH_MU_KM3_S2 = 398600.4415   # identical to GMAT's JGM3.cof
DEFAULT_EPOCH = "01 Jan 2026 00:00:00.000"
SATELLITE = "Sat"

# The propagator the replay imposes: the agent never chooses it.
INTEGRATOR = "PrinceDormand78"
ACCURACY = 1e-12
