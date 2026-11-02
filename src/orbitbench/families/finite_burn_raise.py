# src/orbitbench/families/finite_burn_raise.py
"""Raise the apoapsis with one long burn: the impulsive formula is a first guess, and gravity losses make it fall short."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer, FiniteBurn
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, fill, finite_answer_format, load_template
from orbitbench.reference.finite_burn import (GMAT_THRUSTER_G0_M_S2, apoapsis_after, duration_for_apoapsis,
                                              mass_flow_kg_s)

MAX_DRAWS = 1000


class FiniteBurnRaiseFamily(Family):
    name = "finite_burn_raise"

    def __init__(self):
        self.template = load_template("finite_burn_raise")

    def _mass_kg(self) -> float:
        return self.template["dry_mass_kg"] + self.template["fuel_kg"]

    def _draw(self, seed: int) -> dict:
        """Orbit, target and engine from the seed; a target that needs more than the allowed share of the tank is redrawn."""
        tpl, rng = self.template, np.random.default_rng(seed)
        rg = tpl["ranges"]
        for _ in range(MAX_DRAWS):
            p = {k: round(float(rng.uniform(*rg[k])), 1) for k in ("r1_km", "inc_deg", "raan_deg", "ta_deg",
                                                                  "thrust_n", "isp_s")}
            p["ra_km"] = round(p["r1_km"] * float(rng.uniform(*rg["apoapsis_factor"])), 1)
            longest = tpl["max_fuel_fraction"] * tpl["fuel_kg"] / mass_flow_kg_s(p["thrust_n"], p["isp_s"])
            if apoapsis_after(p["r1_km"], p["thrust_n"], p["isp_s"], self._mass_kg(), longest) < p["ra_km"]:
                continue
            p["duration_s"] = round(duration_for_apoapsis(p["r1_km"], p["ra_km"], p["thrust_n"], p["isp_s"],
                                                          self._mass_kg(), longest), 3)
            return p
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "finite":
            raise ValueError("finite_burn_raise is answered with finite burns only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        ra_tol = round(tol["apoapsis_rel"] * p["ra_km"], 1)
        final_epoch = add_seconds(tpl["epoch"], 1.5 * p["duration_s"] + tpl["final_margin_s"])
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      dry_kg=tpl["dry_mass_kg"], fuel_kg=tpl["fuel_kg"], g0=GMAT_THRUSTER_G0_M_S2, ra_tol_km=ra_tol,
                      inc_tol=tol["inc_deg"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["finite"], fields),
                                 finite_answer_format(SATELLITE)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["r1_km"], "ecc": 0.0, "inc_deg": p["inc_deg"],
                           "raan_deg": p["raan_deg"], "aop_deg": 0.0, "ta_deg": p["ta_deg"]},
            constraints=[{"quantity": "ra_km", "target": p["ra_km"], "abs_tol": ra_tol},
                         {"quantity": "inc_deg", "target": p["inc_deg"], "abs_tol": tol["inc_deg"]}],
            params=p,
            propulsion={"dry_mass_kg": tpl["dry_mass_kg"], "tanks": [{"name": "Tank", "fuel_mass_kg": tpl["fuel_kg"]}],
                        "thrusters": [{"name": "Thr", "tank": "Tank", "thrust_n": p["thrust_n"], "isp_s": p["isp_s"]}]})

    def reference(self, instance: Instance) -> FinalAnswer:
        burn = FiniteBurn(epoch_utc=instance.epoch, spacecraft=instance.satellite,
                          duration_s=instance.params["duration_s"], direction="prograde")
        return FinalAnswer(schema_version="1.0", status="solved", finite_burns=[burn],
                           claims=Claims(verified=True, method="integrated_thrust"))
