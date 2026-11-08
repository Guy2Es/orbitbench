# src/orbitbench/families/lunar_draw.py
"""The candidate stream of lunar_impact, numpy only: the table builder runs this file inside the GMAT container."""
from datetime import datetime, timedelta

import numpy as np

MOON_RADIUS_KM = 1737.4
ELEMENTS = ("sma_km", "ecc", "inc_deg", "raan_deg", "aop_deg", "ta_deg")


def candidates(seed: int, ranges: dict, epoch_start: str, epoch_days: float):
    """Endless stream of candidate orbits for `seed`, rounded the way the statement prints them.

    The periapsis altitude is drawn directly, so the semi-major axis follows from it and the eccentricity."""
    rng = np.random.default_rng(seed)
    start = datetime.strptime(epoch_start, "%d %b %Y %H:%M:%S.%f")
    while True:
        alt = rng.uniform(*ranges["periapsis_alt_km"])
        ecc = round(float(rng.uniform(*ranges["ecc"])), 4)
        p = {"sma_km": round((MOON_RADIUS_KM + float(alt)) / (1.0 - ecc), 2), "ecc": ecc}
        for k in ("inc_deg", "raan_deg", "aop_deg", "ta_deg"):
            p[k] = round(float(rng.uniform(*ranges[k])), 1)
        when = start + timedelta(seconds=round(float(rng.uniform(0, epoch_days)) * 1440) * 60)
        p["epoch"] = when.strftime("%d %b %Y %H:%M:%S.000")
        yield p
