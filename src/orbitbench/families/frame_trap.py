# src/orbitbench/families/frame_trap.py
"""A tangential burn that must be written in LVLH, where the along-track axis is the second component, not the first."""
import math

import numpy as np

from orbitbench.answer import Claims, FinalAnswer, Maneuver
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template


def tangential_dv_km_s(r_km: float, other_apsis_km: float, mu: float = EARTH_MU_KM3_S2) -> float:
    """Signed burn along the velocity from the circular orbit of radius `r_km` to an orbit whose other apsis is given."""
    a = (r_km + other_apsis_km) / 2.0
    return math.sqrt(mu * (2.0 / r_km - 1.0 / a)) - math.sqrt(mu / r_km)


class FrameTrapFamily(Family):
    name = "frame_trap"

    def __init__(self):
        self.template = load_template("frame_trap")

    def _draw(self, seed: int) -> dict:
        """An even seed raises the apoapsis (a forward burn), an odd one lowers the periapsis (a retrograde burn)."""
        tpl, rng = self.template, np.random.default_rng(seed)
        rg = tpl["ranges"]
        while True:
            r = round(float(rng.uniform(*rg["r_km"])), 1)
            inc, raan, ta = (round(float(rng.uniform(*rg[k])), 1) for k in ("inc_deg", "raan_deg", "ta_deg"))
            if seed % 2 == 0:
                other = round(r * float(rng.uniform(*rg["apoapsis_factor"])), 1)
                rp, ra = r, other
            else:
                other = round(r * float(rng.uniform(*rg["periapsis_factor"])), 1)
                if other < tpl["min_periapsis_km"]:
                    continue
                rp, ra = other, r
            return {"r_km": r, "inc_deg": inc, "raan_deg": raan, "ta_deg": ta, "rp_km": rp, "ra_km": ra,
                    "other_apsis_km": other, "direction": "forward" if seed % 2 == 0 else "retrograde"}

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "maneuvers":
            raise ValueError("frame_trap is answered with a maneuver plan only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        dv = tangential_dv_km_s(p["r_km"], p["other_apsis_km"])
        budget = round(abs(dv) * 1000.0 + tpl["dv_margin_m_s"], 1)
        goal = (f"raise the apoapsis radius to {p['ra_km']} km, keeping the periapsis radius at {p['rp_km']} km"
                if p["direction"] == "forward" else
                f"lower the periapsis radius to {p['rp_km']} km, keeping the apoapsis radius at {p['ra_km']} km")
        final_epoch = add_seconds(tpl["epoch"], tpl["final_margin_s"])
        apsis_tol = round(tol["apsis_rel"] * p["r_km"], 3)
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      budget_m_s=budget, apsis_tol_km=apsis_tol, inc_tol=tol["inc_deg"], goal=goal, **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["maneuvers"], fields),
                                 answer_format(mode, SATELLITE)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["r_km"], "ecc": 0.0, "inc_deg": p["inc_deg"],
                           "raan_deg": p["raan_deg"], "aop_deg": 0.0, "ta_deg": p["ta_deg"]},
            constraints=[{"quantity": "rp_km", "target": p["rp_km"], "abs_tol": apsis_tol},
                         {"quantity": "ra_km", "target": p["ra_km"], "abs_tol": apsis_tol},
                         {"quantity": "inc_deg", "target": p["inc_deg"], "abs_tol": tol["inc_deg"]},
                         {"quantity": "plan_delta_v_m_s", "max": budget}],
            params={**p, "budget_m_s": budget})

    def reference(self, instance: Instance) -> FinalAnswer:
        p = instance.params
        burn = Maneuver(epoch_utc=instance.epoch, spacecraft=instance.satellite, frame="LVLH",
                        delta_v_km_s=[0.0, tangential_dv_km_s(p["r_km"], p["other_apsis_km"]), 0.0])
        return FinalAnswer(schema_version="1.0", status="solved", maneuvers=[burn],
                           claims=Claims(verified=True, method="tangential_burn"))

    def reference_delta_v_m_s(self, instance: Instance) -> float:
        p = instance.params
        return abs(tangential_dv_km_s(p["r_km"], p["other_apsis_km"])) * 1000.0
