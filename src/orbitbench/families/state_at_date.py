# src/orbitbench/families/state_at_date.py
"""The inertial state of a spacecraft on an eccentric Earth orbit some hours after the given elements."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.kepler import propagate

KEYS = ("x_km", "y_km", "z_km", "vx_km_s", "vy_km_s", "vz_km_s")
MAX_DRAWS = 1000


class StateAtDateFamily(Family):
    name = "state_at_date"

    def __init__(self):
        self.template = load_template("state_at_date")

    def _draw(self, seed: int) -> dict:
        """Elements and time of flight from the seed; orbits that dip into the atmosphere are redrawn."""
        rg, rng = self.template["ranges"], np.random.default_rng(seed)
        for _ in range(MAX_DRAWS):
            p = {k: round(float(rng.uniform(*rg[k])), 1 if k != "ecc" else 3)
                 for k in ("sma_km", "ecc", "inc_deg", "raan_deg", "aop_deg", "ta_deg")}
            p["dt_s"] = round(float(rng.uniform(*rg["dt_hours"])) * 3600.0)
            if p["sma_km"] * (1.0 - p["ecc"]) >= self.template["min_periapsis_km"]:
                return p
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "values":
            raise ValueError("state_at_date is answered with values only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]
        final_epoch = add_seconds(tpl["epoch"], p["dt_s"])
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, epoch=tpl["epoch"], final_epoch=final_epoch,
                      pos_tol=tol["position_km"], vel_tol=tol["velocity_km_s"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["values"], fields),
                                 answer_format(mode, SATELLITE, KEYS)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", **{k: p[k] for k in
                                                    ("sma_km", "ecc", "inc_deg", "raan_deg", "aop_deg", "ta_deg")}},
            tolerances={k: tol["position_km"] if k.endswith("_km") else tol["velocity_km_s"] for k in KEYS},
            params=p)

    def reference_values(self, instance: Instance) -> dict:
        p = instance.params
        pos, vel = propagate(p["sma_km"], p["ecc"], p["inc_deg"], p["raan_deg"], p["aop_deg"], p["ta_deg"], p["dt_s"])
        return dict(zip(KEYS, [float(c) for c in (*pos, *vel)]))

    def reference(self, instance: Instance) -> FinalAnswer:
        return FinalAnswer(schema_version="1.0", status="solved", values=self.reference_values(instance),
                           claims=Claims(verified=True, method="kepler_equation"))
