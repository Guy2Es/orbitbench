# src/orbitbench/families/canary.py
"""Three trivial one-formula questions. They are played with every run and never counted in its results: if a model
fails one, the harness (a tool, the sandbox, the reply parsing) is broken, not the model."""
import math

import numpy as np

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template

KINDS = ("circular_speed", "period", "escape_speed")
UNITS = {"circular_speed": ("circular_speed_m_s", "m/s"), "period": ("period_s", "s"),
         "escape_speed": ("escape_speed_m_s", "m/s")}


def exact(kind: str, r_km: float) -> float:
    if kind == "circular_speed":
        return 1000.0 * math.sqrt(EARTH_MU_KM3_S2 / r_km)
    if kind == "period":
        return 2.0 * math.pi * math.sqrt(r_km**3 / EARTH_MU_KM3_S2)
    return 1000.0 * math.sqrt(2.0 * EARTH_MU_KM3_S2 / r_km)


class CanaryFamily(Family):
    name = "canary"

    def __init__(self):
        self.template = load_template("canary")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "values":
            raise ValueError("canary is answered with values only")
        tpl, kind = self.template, KINDS[seed % len(KINDS)]
        r_km = round(float(np.random.default_rng(seed).uniform(*tpl["ranges"]["r_km"])), 1)
        key, unit = UNITS[kind]
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], r_km=r_km, key=key, unit=unit,
                      rel_tol_pct=100 * tpl["tolerance"]["relative"])
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"][kind], fields),
                                 answer_format("values", SATELLITE, (key,))])
        tol = round(tpl["tolerance"]["relative"] * exact(kind, r_km), 3)
        return Instance(
            family=self.name, mode=mode, seed=seed, level=1, statement=statement, epoch=tpl["epoch"],
            final_epoch=add_seconds(tpl["epoch"], tpl["final_margin_s"]), satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": r_km, "ecc": 0.0, "inc_deg": 0.0, "raan_deg": 0.0,
                           "aop_deg": 0.0, "ta_deg": 0.0},
            tolerances={key: tol}, params={"kind": kind, "r_km": r_km})

    def reference_values(self, instance: Instance) -> dict:
        p = instance.params
        return {UNITS[p["kind"]][0]: exact(p["kind"], p["r_km"])}

    def reference(self, instance: Instance) -> FinalAnswer:
        return FinalAnswer(schema_version="1.0", status="solved", values=self.reference_values(instance),
                           claims=Claims(verified=True, method="closed_form"))
