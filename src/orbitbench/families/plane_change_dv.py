# src/orbitbench/families/plane_change_dv.py
"""Inclination change of a circular Earth orbit at a node, answered as a number or as a one-burn plan."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer, Maneuver
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import MODES, Family, Instance, answer_format, fill, load_template
from orbitbench.reference.plane_change import plane_change


class PlaneChangeDvFamily(Family):
    name = "plane_change_dv"

    def __init__(self):
        self.template = load_template("plane_change_dv")

    def _draw(self, seed: int) -> dict:
        """Radius, inclination and its change from the seed. Raising or lowering the inclination is a coin flip."""
        rg, rng = self.template["ranges"], np.random.default_rng(seed)
        r = round(float(rng.uniform(*rg["r_km"])), 1)
        inc1 = round(float(rng.uniform(*rg["inc1_deg"])), 1)
        delta = round(float(rng.uniform(*rg["delta_inc_deg"])), 1)
        sign = 1.0 if (inc1 - delta < 0.0 or rng.random() < 0.5) else -1.0
        return {"r_km": r, "inc1_deg": inc1, "inc2_deg": round(inc1 + sign * delta, 1)}

    def generate(self, seed: int, mode: str) -> Instance:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        final_epoch = add_seconds(tpl["epoch"], tpl["final_margin_s"])
        sma_tol = round(tol["sma_rel"] * p["r_km"], 3)
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      dv_tol=tol["delta_v_total_m_s"], sma_tol_km=sma_tol, ecc_max=tol["ecc_max"],
                      inc_tol=tol["inc_deg"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"][mode], fields),
                                 answer_format(mode, SATELLITE)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["r_km"], "ecc": 0.0, "inc_deg": p["inc1_deg"],
                           "raan_deg": 0.0, "aop_deg": 0.0, "ta_deg": 0.0},
            constraints=[{"quantity": "sma_km", "target": p["r_km"], "abs_tol": sma_tol},
                         {"quantity": "ecc", "max": tol["ecc_max"]},
                         {"quantity": "inc_deg", "target": p["inc2_deg"], "abs_tol": tol["inc_deg"]}],
            tolerances={"delta_v_total_m_s": tol["delta_v_total_m_s"]}, params=p)

    def reference(self, instance: Instance) -> FinalAnswer:
        p = instance.params
        change = plane_change(p["r_km"], p["inc1_deg"], p["inc2_deg"])
        claims = Claims(verified=True, method="closed_form")
        values = {"delta_v_total_m_s": change.total_m_s}
        if instance.mode == "values":
            return FinalAnswer(schema_version="1.0", status="solved", values=values, claims=claims)
        burn = Maneuver(epoch_utc=instance.epoch, spacecraft=instance.satellite, frame="VNB",
                        delta_v_km_s=[change.along_velocity_km_s, change.along_normal_km_s, 0.0])
        return FinalAnswer(schema_version="1.0", status="solved", values=values, maneuvers=[burn], claims=claims)

    def reference_values(self, instance: Instance) -> dict:
        return {"delta_v_total_m_s": self.reference_delta_v_m_s(instance)}

    def reference_delta_v_m_s(self, instance: Instance) -> float:
        p = instance.params
        return plane_change(p["r_km"], p["inc1_deg"], p["inc2_deg"]).total_m_s
