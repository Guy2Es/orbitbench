# src/orbitbench/families/sun_synchronous.py
"""Choose the inclination that makes an orbit sun-synchronous; the grader flies it in GMAT and measures the node drift."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import EARTH_J2, EARTH_MU_KM3_S2, EARTH_RADIUS_KM, SATELLITE, SUN_RATE_DEG_DAY
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.sun_synchronous import (inclination_formula, inclination_numeric, measured_drift_deg_day,
                                                  orbit_period_s)

ELEMENTS = ("sma_km", "ecc", "raan_deg", "aop_deg", "ta_deg")
MAX_DRAWS = 1000


class SunSynchronousFamily(Family):
    name = "sun_synchronous"

    def __init__(self):
        self.template = load_template("sun_synchronous")

    def _n_orbits(self, sma_km: float) -> int:
        return round(self.template["measure_days"] * 86400.0 / orbit_period_s(sma_km))

    def _draw(self, seed: int) -> dict:
        """Elements from the seed. Orbits that dip into the atmosphere, that admit no sun-synchronous inclination, or
        whose secular-formula answer drifts too far from the Sun's rate when integrated, are redrawn."""
        tpl, rng = self.template, np.random.default_rng(seed)
        rg = tpl["ranges"]
        for _ in range(MAX_DRAWS):
            p = {k: round(float(rng.uniform(*rg[k])), 1 if k != "ecc" else 3) for k in ELEMENTS}
            if p["sma_km"] * (1.0 - p["ecc"]) < tpl["min_periapsis_km"]:
                continue
            try:
                formula = inclination_formula(p["sma_km"], p["ecc"])
            except ValueError:
                continue
            drift = measured_drift_deg_day(p["sma_km"], p["ecc"], formula, p["raan_deg"], p["aop_deg"], p["ta_deg"],
                                           self._n_orbits(p["sma_km"]))
            if abs(drift - SUN_RATE_DEG_DAY) > tpl["formula_agreement_deg_day"]:
                continue
            return p
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "orbit":
            raise ValueError("sun_synchronous is answered with an orbit only")
        tpl, p = self.template, self._draw(seed)
        tol = tpl["tolerance"]["drift_deg_day"]
        n_orbits = self._n_orbits(p["sma_km"])
        final_epoch = add_seconds(tpl["epoch"], n_orbits * orbit_period_s(p["sma_km"]))
        fields = dict(satellite=SATELLITE, mu=EARTH_MU_KM3_S2, radius=EARTH_RADIUS_KM, j2=f"{EARTH_J2:.10e}",
                      epoch=tpl["epoch"], final_epoch=final_epoch, n_orbits=n_orbits, drift_tol=tol,
                      sun_rate=f"{SUN_RATE_DEG_DAY:.6f}", **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["orbit"], fields),
                                 answer_format(mode, SATELLITE, ("inc_deg",))])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=tpl["epoch"], final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "keplerian", **{k: p[k] for k in ELEMENTS}},   # the inclination is the answer
            constraints=[{"quantity": "raan_drift_deg_day", "target": SUN_RATE_DEG_DAY, "abs_tol": tol}],
            params={**p, "n_orbits": n_orbits}, gravity={"degree": 2, "order": 0, "file": "JGM3"})

    def reference_formula(self, instance: Instance) -> float:
        """Inclination from the secular formula: the second, independent reference."""
        p = instance.params
        return inclination_formula(p["sma_km"], p["ecc"])

    def reference_inclination(self, instance: Instance) -> float:
        """Inclination whose integrated drift is exactly the Sun's, for these elements and this duration."""
        p = instance.params
        return inclination_numeric(p["sma_km"], p["ecc"], p["raan_deg"], p["aop_deg"], p["ta_deg"], p["n_orbits"])

    def reference(self, instance: Instance) -> FinalAnswer:
        return FinalAnswer(schema_version="1.0", status="solved",
                           initial_orbit={"inc_deg": self.reference_inclination(instance)},
                           claims=Claims(verified=True, method="numerical_search_on_j2_drift"))
