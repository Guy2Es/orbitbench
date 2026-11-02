# src/orbitbench/families/hohmann.py
"""Hohmann transfer between two circular coplanar Earth orbits, answered as a number or as a maneuver plan."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer, Maneuver
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import MODES, Family, Instance, answer_format, fill, load_template
from orbitbench.reference.hohmann import hohmann

MAX_DRAWS = 1000


class HohmannFamily(Family):
    name = "hohmann"

    def __init__(self):
        self.template = load_template("hohmann")

    def _draw(self, seed: int) -> dict:
        """Radii and inclination from the seed; degenerate draws (too close, too low, beyond GEO) are redrawn."""
        rg, rng = self.template["ranges"], np.random.default_rng(seed)
        for _ in range(MAX_DRAWS):
            r1 = round(float(rng.uniform(*rg["r1_km"])), 1)
            r2 = round(float(rng.uniform(*rg["r2_km"])), 1)
            inc = round(float(rng.uniform(*rg["inc_deg"])), 1)
            if r2 / r1 >= self.template["min_radius_ratio"]:
                return {"r1_km": r1, "r2_km": r2, "inc_deg": inc}
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        transfer = hohmann(p["r1_km"], p["r2_km"])
        final_epoch = add_seconds(tpl["epoch"], transfer.transfer_time_s + tpl["final_margin_s"])
        sma_tol = round(tol["sma_rel"] * p["r2_km"], 3)
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      dv_tol=tol["delta_v_total_m_s"], sma_tol_km=sma_tol, ecc_max=tol["ecc_max"],
                      inc_tol=tol["inc_deg"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"][mode], fields),
                                 answer_format(mode, SATELLITE)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["r1_km"], "ecc": 0.0, "inc_deg": p["inc_deg"],
                           "raan_deg": 0.0, "aop_deg": 0.0, "ta_deg": 0.0},
            constraints=[{"quantity": "sma_km", "target": p["r2_km"], "abs_tol": sma_tol},
                         {"quantity": "ecc", "max": tol["ecc_max"]},
                         {"quantity": "inc_deg", "target": p["inc_deg"], "abs_tol": tol["inc_deg"]}],
            tolerances={"delta_v_total_m_s": tol["delta_v_total_m_s"]}, params=p)

    def reference(self, instance: Instance) -> FinalAnswer:
        p = instance.params
        transfer = hohmann(p["r1_km"], p["r2_km"])
        claims = Claims(verified=True, method="closed_form")
        if instance.mode == "values":
            return FinalAnswer(schema_version="1.0", status="solved",
                               values={"delta_v_total_m_s": transfer.total_m_s}, claims=claims)
        burns = [Maneuver(epoch_utc=instance.epoch, spacecraft=instance.satellite, frame="VNB",
                          delta_v_km_s=[transfer.delta_v1_km_s, 0.0, 0.0]),
                 Maneuver(epoch_utc=add_seconds(instance.epoch, transfer.transfer_time_s),
                          spacecraft=instance.satellite, frame="VNB",
                          delta_v_km_s=[transfer.delta_v2_km_s, 0.0, 0.0])]
        return FinalAnswer(schema_version="1.0", status="solved", values={"delta_v_total_m_s": transfer.total_m_s},
                           maneuvers=burns, claims=claims)

    def reference_values(self, instance: Instance) -> dict:
        return {"delta_v_total_m_s": self.reference_delta_v_m_s(instance)}

    def reference_delta_v_m_s(self, instance: Instance) -> float:
        return hohmann(instance.params["r1_km"], instance.params["r2_km"]).total_m_s
