# src/orbitbench/families/escape_velocity.py
"""Delta-v to reach escape speed from a circular orbit. A training family: analytical, answered with a number."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.tsiolkovsky import escape_delta_v_m_s

KEYS = ("delta_v_escape_m_s",)


class EscapeVelocityFamily(Family):
    name = "escape_velocity"

    def __init__(self):
        self.template = load_template("escape_velocity")

    def _draw(self, seed: int) -> dict:
        rg, rng = self.template["ranges"], np.random.default_rng(seed)
        return {"r_km": round(float(rng.uniform(*rg["r_km"])), 1), "inc_deg": round(float(rng.uniform(*rg["inc_deg"])), 1)}

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "values":
            raise ValueError("escape_velocity is answered with values only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]["delta_v_escape_m_s"]
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], dv_tol=tol, **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["values"], fields),
                                 answer_format(mode, SATELLITE, KEYS)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=tpl["epoch"], satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["r_km"], "ecc": 0.0, "inc_deg": p["inc_deg"],
                           "raan_deg": 0.0, "aop_deg": 0.0, "ta_deg": 0.0},
            tolerances={"delta_v_escape_m_s": tol}, params=p)

    def reference_values(self, instance: Instance) -> dict:
        return {"delta_v_escape_m_s": escape_delta_v_m_s(instance.params["r_km"], EARTH_MU_KM3_S2)}

    def reference(self, instance: Instance) -> FinalAnswer:
        return FinalAnswer(schema_version="1.0", status="solved", values=self.reference_values(instance),
                           claims=Claims(verified=True, method="closed_form"))
