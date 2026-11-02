# src/orbitbench/families/plane_change_budget_plan.py
"""A transfer with a plane change under a propellant budget: only the plane change shared between the burns fits."""
import math

import numpy as np

from orbitbench.answer import Claims, FinalAnswer, Maneuver
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.plane_change_budget import (best_split, rocket_delta_v_m_s, separate_plane_change_m_s,
                                                      split_transfer)

MAX_DRAWS = 5000


def simple_strategies_m_s(r1_km: float, r2_km: float, plane_change_deg: float) -> dict:
    """What the unoptimised plans cost, in m/s."""
    return {"all_at_apoapsis": split_transfer(r1_km, r2_km, plane_change_deg, 0.0).total_m_s,
            "all_at_periapsis": split_transfer(r1_km, r2_km, plane_change_deg, plane_change_deg).total_m_s,
            "separate": separate_plane_change_m_s(r1_km, r2_km, plane_change_deg)}


class PlaneChangeBudgetPlanFamily(Family):
    name = "plane_change_budget_plan"

    def __init__(self):
        self.template = load_template("plane_change_budget_plan")

    def _draw(self, seed: int) -> dict:
        """Radii, plane change and spacecraft from the seed; the fuel is sized to the optimum plus a small margin."""
        tpl, rng = self.template, np.random.default_rng(seed)
        rg, g0 = tpl["ranges"], tpl["g0_m_s2"]
        for _ in range(MAX_DRAWS):
            r1, r2 = (round(float(rng.uniform(*rg[k])), 1) for k in ("r1_km", "r2_km"))
            inc, change = (round(float(rng.uniform(*rg[k])), 1) for k in ("inc_deg", "plane_change_deg"))
            mass, isp = (round(float(rng.uniform(*rg[k]))) for k in ("initial_mass_kg", "isp_s"))
            best = best_split(r1, r2, change).total_m_s
            fuel = round(mass * (1.0 - math.exp(-(best + tpl["dv_margin_m_s"]) / (isp * g0))), 2)
            budget = rocket_delta_v_m_s(mass, fuel, isp)
            if not best + 0.5 * tpl["dv_margin_m_s"] <= budget <= best + 1.5 * tpl["dv_margin_m_s"]:
                continue
            if min(simple_strategies_m_s(r1, r2, change).values()) - budget < tpl["min_strategy_gap_m_s"] - tpl["dv_margin_m_s"]:
                continue
            return {"r1_km": r1, "r2_km": r2, "inc_deg": inc, "plane_change_deg": change, "final_inc_deg": round(inc + change, 1),
                    "initial_mass_kg": mass, "isp_s": isp, "fuel_mass_kg": fuel, "g0_m_s2": g0, "budget_m_s": round(budget, 3)}
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "maneuvers":
            raise ValueError("plane_change_budget_plan is answered with a maneuver plan only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        best = best_split(p["r1_km"], p["r2_km"], p["plane_change_deg"])
        final_epoch = add_seconds(tpl["epoch"], best.transfer_time_s + tpl["final_margin_s"])
        sma_tol = round(tol["sma_rel"] * p["r2_km"], 3)
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      sma_tol_km=sma_tol, ecc_max=tol["ecc_max"], inc_tol=tol["inc_deg"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["maneuvers"], fields),
                                 answer_format(mode, SATELLITE)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["r1_km"], "ecc": 0.0, "inc_deg": p["inc_deg"],
                           "raan_deg": 0.0, "aop_deg": 0.0, "ta_deg": 0.0},
            constraints=[{"quantity": "sma_km", "target": p["r2_km"], "abs_tol": sma_tol},
                         {"quantity": "ecc", "max": tol["ecc_max"]},
                         {"quantity": "inc_deg", "target": p["final_inc_deg"], "abs_tol": tol["inc_deg"]},
                         {"quantity": "plan_delta_v_m_s", "max": p["budget_m_s"]}],
            params=p)

    def reference(self, instance: Instance) -> FinalAnswer:
        p = instance.params
        t = best_split(p["r1_km"], p["r2_km"], p["plane_change_deg"])
        plan = [(0.0, t.burn1_km_s), (t.transfer_time_s, t.burn2_km_s)]
        burns = [Maneuver(epoch_utc=add_seconds(instance.epoch, when), spacecraft=instance.satellite, frame="VNB",
                          delta_v_km_s=[dv[0], dv[1], 0.0]) for when, dv in plan]
        return FinalAnswer(schema_version="1.0", status="solved", maneuvers=burns,
                           claims=Claims(verified=True, method="split_plane_change"))

    def reference_delta_v_m_s(self, instance: Instance) -> float:
        p = instance.params
        return best_split(p["r1_km"], p["r2_km"], p["plane_change_deg"]).total_m_s
