# src/orbitbench/families/guess_trap_transfer.py
"""A Hohmann transfer whose suggested starting value for the first burn is beyond escape: a GMAT Target from it diverges."""
import math

import numpy as np

from orbitbench.answer import Claims, FinalAnswer, Maneuver
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.hohmann import hohmann

MAX_DRAWS = 1000


def escape_burn_km_s(r_km: float, mu: float = EARTH_MU_KM3_S2) -> float:
    """The burn along the velocity that takes a circular orbit of radius `r_km` to escape speed."""
    return (math.sqrt(2.0) - 1.0) * math.sqrt(mu / r_km)


class GuessTrapTransferFamily(Family):
    name = "guess_trap_transfer"

    def __init__(self):
        self.template = load_template("guess_trap_transfer")

    def _draw(self, seed: int) -> dict:
        tpl, rng = self.template, np.random.default_rng(seed)
        rg = tpl["ranges"]
        for _ in range(MAX_DRAWS):
            r1 = round(float(rng.uniform(*rg["r1_km"])), 1)
            r2 = round(float(rng.uniform(*rg["r2_km"])), 1)
            inc = round(float(rng.uniform(*rg["inc_deg"])), 1)
            factor = float(rng.uniform(*rg["guess_over_escape"]))
            if r2 / r1 >= tpl["min_radius_ratio"]:
                return {"r1_km": r1, "r2_km": r2, "inc_deg": inc,
                        "guess_km_s": round(factor * escape_burn_km_s(r1), 3)}
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "maneuvers":
            raise ValueError("guess_trap_transfer is answered with a maneuver plan only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        transfer = hohmann(p["r1_km"], p["r2_km"])
        budget = round(transfer.total_m_s + tpl["dv_margin_m_s"], 1)
        final_epoch = add_seconds(tpl["epoch"], transfer.transfer_time_s + tpl["final_margin_s"])
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
        t = hohmann(p["r1_km"], p["r2_km"])
        burns = [Maneuver(epoch_utc=add_seconds(instance.epoch, when), spacecraft=instance.satellite, frame="VNB",
                          delta_v_km_s=[dv, 0.0, 0.0])
                 for when, dv in ((0.0, t.delta_v1_km_s), (t.transfer_time_s, t.delta_v2_km_s))]
        return FinalAnswer(schema_version="1.0", status="solved", maneuvers=burns,
                           claims=Claims(verified=True, method="closed_form"))

    def reference_delta_v_m_s(self, instance: Instance) -> float:
        p = instance.params
        return hohmann(p["r1_km"], p["r2_km"]).total_m_s
