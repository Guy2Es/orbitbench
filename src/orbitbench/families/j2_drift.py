# src/orbitbench/families/j2_drift.py
"""The node and periapsis of an Earth orbit a few days later under point mass plus J2 gravity."""
import math

import numpy as np

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import EARTH_J2, EARTH_MU_KM3_S2, EARTH_RADIUS_KM, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.j2 import elements_from_state, propagate_j2

KEYS = ("raan_deg", "aop_deg")
ELEMENTS = ("sma_km", "ecc", "inc_deg", "raan_deg", "aop_deg", "ta_deg")
MAX_DRAWS = 1000
GRAVITY = {"degree": 2, "order": 0, "file": "JGM3"}


def _near_wrap(angle_deg: float, margin_deg: float) -> bool:
    return min(angle_deg, 360.0 - angle_deg) < margin_deg


class J2DriftFamily(Family):
    name = "j2_drift"

    def __init__(self):
        self.template = load_template("j2_drift")

    def _draw(self, seed: int) -> dict:
        """Elements and duration from the seed. Orbits that dip into the atmosphere, and answers that sit within
        a degree of the 0/360 wrap (where an equivalent answer would read as a huge error) or whose node barely
        moves (so that a 1 % error on the drift would hide inside the tolerance), are redrawn."""
        tpl, rng = self.template, np.random.default_rng(seed)
        rg = tpl["ranges"]
        for _ in range(MAX_DRAWS):
            p = {k: round(float(rng.uniform(*rg[k])), 1 if k != "ecc" else 3) for k in ELEMENTS}
            p["dt_days"] = int(rng.integers(rg["dt_days"][0], rg["dt_days"][1] + 1))
            if p["sma_km"] * (1.0 - p["ecc"]) < tpl["min_periapsis_km"]:
                continue
            exact = self._exact(p)
            if any(_near_wrap(exact[k], tpl["wrap_margin_deg"]) for k in KEYS):
                continue
            if abs(math.remainder(exact["raan_deg"] - p["raan_deg"], 360.0)) < tpl["min_node_drift_deg"]:
                continue
            return p
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    @staticmethod
    def _exact(p: dict) -> dict:
        pos, vel = propagate_j2(*(p[k] for k in ELEMENTS), p["dt_days"] * 86400.0)
        return elements_from_state(pos, vel)

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "values":
            raise ValueError("j2_drift is answered with values only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]["angle_deg"]
        final_epoch = add_seconds(tpl["epoch"], p["dt_days"] * 86400)
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, radius=EARTH_RADIUS_KM, j2=f"{EARTH_J2:.10e}",
                      epoch=tpl["epoch"], final_epoch=final_epoch, angle_tol=tol, **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["values"], fields),
                                 answer_format(mode, SATELLITE, KEYS)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", **{k: p[k] for k in ELEMENTS}},
            tolerances={k: tol for k in KEYS}, params=p, gravity=dict(GRAVITY))

    def reference_values(self, instance: Instance) -> dict:
        exact = self._exact(instance.params)
        return {k: float(exact[k]) for k in KEYS}

    def reference(self, instance: Instance) -> FinalAnswer:
        return FinalAnswer(schema_version="1.0", status="solved", values=self.reference_values(instance),
                           claims=Claims(verified=True, method="numerical_integration_j2"))
