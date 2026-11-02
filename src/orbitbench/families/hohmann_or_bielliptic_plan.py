# src/orbitbench/families/hohmann_or_bielliptic_plan.py
"""A transfer to a high circular orbit where Hohmann or a bi-elliptic transfer is the cheaper, depending on the radii."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer, Maneuver
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.bielliptic import best_bielliptic
from orbitbench.reference.hohmann import hohmann

MAX_DRAWS = 5000


def costs(r1_km: float, r2_km: float, ra_max_km: float) -> tuple:
    """(Hohmann total, best bi-elliptic total under the bound) in m/s; the bound never excludes Hohmann."""
    return hohmann(r1_km, r2_km).total_m_s, best_bielliptic(r1_km, r2_km, ra_max_km).total_m_s


class HohmannOrBiellipticPlanFamily(Family):
    name = "hohmann_or_bielliptic_plan"

    def __init__(self):
        self.template = load_template("hohmann_or_bielliptic_plan")

    def _draw(self, seed: int) -> dict:
        """Radii and apoapsis bound from the seed. The winning strategy is drawn first, then the radii are redrawn
        until that strategy beats the other one by a clear margin."""
        tpl, rng = self.template, np.random.default_rng(seed)
        rg, wanted = tpl["ranges"], ("hohmann", "bielliptic")[seed % 2]
        for _ in range(MAX_DRAWS):
            r1 = round(float(rng.uniform(*rg["r1_km"])), 1)
            r2 = round(float(rng.uniform(*rg["r2_km"])), 1)
            ra_max = round(r2 * float(rng.uniform(*rg["apoapsis_factor"])), -2)
            inc = round(float(rng.uniform(*rg["inc_deg"])), 1)
            hoh, bi = costs(r1, r2, ra_max)
            if wanted == "bielliptic" and hoh - bi >= tpl["min_strategy_gap_m_s"]:
                return {"r1_km": r1, "r2_km": r2, "ra_max_km": ra_max, "inc_deg": inc, "winner": wanted}
            if wanted == "hohmann" and r2 / r1 <= tpl["max_hohmann_ratio"]:
                return {"r1_km": r1, "r2_km": r2, "ra_max_km": ra_max, "inc_deg": inc, "winner": wanted}
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "maneuvers":
            raise ValueError("hohmann_or_bielliptic_plan is answered with a maneuver plan only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        hoh, bi = costs(p["r1_km"], p["r2_km"], p["ra_max_km"])
        budget = round(min(hoh, bi) + tpl["dv_margin_m_s"], 1)
        end = (hohmann(p["r1_km"], p["r2_km"]).transfer_time_s if p["winner"] == "hohmann"
               else best_bielliptic(p["r1_km"], p["r2_km"], p["ra_max_km"]).time_to_third_burn_s)
        final_epoch = add_seconds(tpl["epoch"], end + tpl["final_margin_s"])
        sma_tol = round(tol["sma_rel"] * p["r2_km"], 3)
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      budget_m_s=budget, sma_tol_km=sma_tol, ecc_max=tol["ecc_max"], inc_tol=tol["inc_deg"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["maneuvers"], fields),
                                 answer_format(mode, SATELLITE)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["r1_km"], "ecc": 0.0, "inc_deg": p["inc_deg"],
                           "raan_deg": 0.0, "aop_deg": 0.0, "ta_deg": 0.0},
            constraints=[{"quantity": "sma_km", "target": p["r2_km"], "abs_tol": sma_tol},
                         {"quantity": "ecc", "max": tol["ecc_max"]},
                         {"quantity": "inc_deg", "target": p["inc_deg"], "abs_tol": tol["inc_deg"]},
                         {"quantity": "plan_delta_v_m_s", "max": budget}],
            params={**p, "budget_m_s": budget})

    def reference(self, instance: Instance) -> FinalAnswer:
        p = instance.params
        claims = Claims(verified=True, method=p["winner"])
        if p["winner"] == "hohmann":
            t = hohmann(p["r1_km"], p["r2_km"])
            plan = [(0.0, t.delta_v1_km_s), (t.transfer_time_s, t.delta_v2_km_s)]
        else:
            t = best_bielliptic(p["r1_km"], p["r2_km"], p["ra_max_km"])
            plan = [(0.0, t.delta_v1_km_s), (t.time_to_second_burn_s, t.delta_v2_km_s),
                    (t.time_to_third_burn_s, t.delta_v3_km_s)]
        burns = [Maneuver(epoch_utc=add_seconds(instance.epoch, when), spacecraft=instance.satellite, frame="VNB",
                          delta_v_km_s=[dv, 0.0, 0.0]) for when, dv in plan]
        return FinalAnswer(schema_version="1.0", status="solved", maneuvers=burns, claims=claims)

    def reference_delta_v_m_s(self, instance: Instance) -> float:
        p = instance.params
        return min(costs(p["r1_km"], p["r2_km"], p["ra_max_km"]))
