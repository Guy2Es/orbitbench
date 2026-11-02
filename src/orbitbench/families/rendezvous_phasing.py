# src/orbitbench/families/rendezvous_phasing.py
"""Catch up with a target ahead on the same circular orbit: two burns on a phasing orbit, whose period the deadline sets."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer, Maneuver
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.rendezvous import best_phasing, target_state, transfer_time_s

MAX_DRAWS = 1000


class RendezvousPhasingFamily(Family):
    name = "rendezvous_phasing"

    def __init__(self):
        self.template = load_template("rendezvous_phasing")

    def _draw(self, seed: int) -> dict:
        """Orbit, phase and deadline from the seed. A deadline for which no phasing orbit stays above the minimum radius
        is redrawn."""
        tpl, rng = self.template, np.random.default_rng(seed)
        rg = tpl["ranges"]
        for _ in range(MAX_DRAWS):
            p = {k: round(float(rng.uniform(*rg[k])), 1) for k in ("sma_km", "inc_deg", "raan_deg", "phase_deg")}
            p["ta_deg"] = round(float(rng.uniform(0.0, 360.0)), 1)
            p["target_ta_deg"] = round((p["ta_deg"] + p["phase_deg"]) % 360.0, 1)
            turns = int(rng.integers(tpl["revolutions"][0], tpl["revolutions"][1] + 1))
            p["duration_s"] = round(transfer_time_s(p["sma_km"], p["phase_deg"], turns), 3)
            if best_phasing(p["sma_km"], p["duration_s"], tpl["min_radius_km"]) is None:
                continue
            return p
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "maneuvers":
            raise ValueError("rendezvous_phasing is answered with a maneuver plan only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        best = best_phasing(p["sma_km"], p["duration_s"], tpl["min_radius_km"])
        budget = round(best.total_m_s + tpl["dv_margin_m_s"], 1)
        final_epoch = add_seconds(tpl["epoch"], p["duration_s"])
        pos, vel = target_state(p["sma_km"], p["inc_deg"], p["raan_deg"], p["target_ta_deg"], p["duration_s"])
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      budget_m_s=budget, pos_tol=tol["position_km"], vel_tol=tol["velocity_m_s"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["maneuvers"], fields),
                                 answer_format(mode, SATELLITE)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["sma_km"], "ecc": 0.0, "inc_deg": p["inc_deg"],
                           "raan_deg": p["raan_deg"], "aop_deg": 0.0, "ta_deg": p["ta_deg"]},
            constraints=[{"quantity": "position_error_km", "point": [float(x) for x in pos], "max": tol["position_km"]},
                         {"quantity": "velocity_error_m_s", "point": [float(x) for x in vel],
                          "max": tol["velocity_m_s"]},
                         {"quantity": "plan_delta_v_m_s", "max": budget}],
            params={**p, "budget_m_s": budget})

    def _best(self, instance: Instance):
        p = instance.params
        return best_phasing(p["sma_km"], p["duration_s"], self.template["min_radius_km"])

    def reference(self, instance: Instance) -> FinalAnswer:
        best = self._best(instance)
        burns = [Maneuver(epoch_utc=when, spacecraft=instance.satellite, frame="VNB", delta_v_km_s=[dv, 0.0, 0.0])
                 for when, dv in ((instance.epoch, best.burn_km_s), (instance.final_epoch, -best.burn_km_s))]
        return FinalAnswer(schema_version="1.0", status="solved", maneuvers=burns,
                           claims=Claims(verified=True, method="phasing_orbit"))

    def reference_delta_v_m_s(self, instance: Instance) -> float:
        return self._best(instance).total_m_s
