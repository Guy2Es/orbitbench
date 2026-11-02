# src/orbitbench/families/circularize_plan.py
"""Circularize an eccentric Earth orbit with one burn: the cheapest is at apoapsis, and its date comes from Kepler."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer, Maneuver
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.circularize import circularize

ELEMENTS = ("sma_km", "ecc", "inc_deg", "raan_deg", "aop_deg", "ta_deg")
MAX_DRAWS = 1000


class CircularizePlanFamily(Family):
    name = "circularize_plan"

    def __init__(self):
        self.template = load_template("circularize_plan")

    def _draw(self, seed: int) -> dict:
        """Elements from the seed; orbits that dip into the atmosphere, or that start at apoapsis, are redrawn."""
        tpl, rng = self.template, np.random.default_rng(seed)
        rg = tpl["ranges"]
        for _ in range(MAX_DRAWS):
            p = {k: round(float(rng.uniform(*rg[k])), 1 if k != "ecc" else 3) for k in ELEMENTS}
            if p["sma_km"] * (1.0 - p["ecc"]) < tpl["min_periapsis_km"]:
                continue
            if abs(p["ta_deg"] - 180.0) < tpl["min_apsis_distance_deg"]:
                continue
            return p
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "maneuvers":
            raise ValueError("circularize_plan is answered with a maneuver plan only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        c = circularize(p["sma_km"], p["ecc"], p["ta_deg"])
        budget = round(c.best_m_s + tpl["dv_margin_m_s"], 1)
        final_epoch = add_seconds(tpl["epoch"], c.time_to_apoapsis_s + tpl["final_margin_s"])
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      budget_m_s=budget, ecc_max=tol["ecc_max"], inc_tol=tol["inc_deg"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["maneuvers"], fields),
                                 answer_format(mode, SATELLITE)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", **{k: p[k] for k in ELEMENTS}},
            constraints=[{"quantity": "ecc", "max": tol["ecc_max"]},
                         {"quantity": "inc_deg", "target": p["inc_deg"], "abs_tol": tol["inc_deg"]},
                         {"quantity": "plan_delta_v_m_s", "max": budget}],
            params={**p, "budget_m_s": budget})

    def reference(self, instance: Instance) -> FinalAnswer:
        p = instance.params
        c = circularize(p["sma_km"], p["ecc"], p["ta_deg"])
        burn = Maneuver(epoch_utc=add_seconds(instance.epoch, c.time_to_apoapsis_s), spacecraft=instance.satellite,
                        frame="VNB", delta_v_km_s=[c.apoapsis_dv_km_s, 0.0, 0.0])
        return FinalAnswer(schema_version="1.0", status="solved", maneuvers=[burn],
                           claims=Claims(verified=True, method="apoapsis_burn"))

    def reference_delta_v_m_s(self, instance: Instance) -> float:
        p = instance.params
        return circularize(p["sma_km"], p["ecc"], p["ta_deg"]).best_m_s
