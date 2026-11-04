# src/orbitbench/families/tsiolkovsky.py
"""Propellant burned for a given delta-v (the rocket equation). A training family: analytical, answered with a number."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import SATELLITE
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.tsiolkovsky import G0_M_S2, propellant_kg

KEYS = ("propellant_mass_kg",)


class TsiolkovskyFamily(Family):
    name = "tsiolkovsky"

    def __init__(self):
        self.template = load_template("tsiolkovsky")

    def _draw(self, seed: int) -> dict:
        rg, rng = self.template["ranges"], np.random.default_rng(seed)
        return {"mass_kg": round(float(rng.uniform(*rg["mass_kg"])), 0),
                "delta_v_m_s": round(float(rng.uniform(*rg["delta_v_m_s"])), 0),
                "isp_s": round(float(rng.uniform(*rg["isp_s"])), 0)}

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "values":
            raise ValueError("tsiolkovsky is answered with values only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]["propellant_mass_kg"]
        fields = dict(satellite=SATELLITE, g0=G0_M_S2, mass_tol=tol, **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["values"], fields),
                                 answer_format(mode, SATELLITE, KEYS)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=tpl["epoch"], satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": 7000.0, "ecc": 0.0, "inc_deg": 0.0,
                           "raan_deg": 0.0, "aop_deg": 0.0, "ta_deg": 0.0},
            tolerances={"propellant_mass_kg": tol}, params=p)

    def reference_values(self, instance: Instance) -> dict:
        p = instance.params
        return {"propellant_mass_kg": propellant_kg(p["mass_kg"], p["delta_v_m_s"], p["isp_s"])}

    def reference(self, instance: Instance) -> FinalAnswer:
        return FinalAnswer(schema_version="1.0", status="solved", values=self.reference_values(instance),
                           claims=Claims(verified=True, method="closed_form"))
