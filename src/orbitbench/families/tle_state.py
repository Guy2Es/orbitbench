# src/orbitbench/families/tle_state.py
"""The TEME state of a satellite some minutes after the epoch of a synthetic TLE, read with SGP4."""
import numpy as np

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import EARTH_MU_KM3_S2, SATELLITE
from orbitbench.epoch import add_seconds
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.reference.tle import build_tle, sgp4_state

KEYS = ("x_km", "y_km", "z_km", "vx_km_s", "vy_km_s", "vz_km_s")
MAX_DRAWS = 1000
YEAR = 2026
LINE_BREAK = "@@"   # `fill` doubles newlines; the two TLE lines are joined after it


class TleStateFamily(Family):
    name = "tle_state"

    def __init__(self):
        self.template = load_template("tle_state")

    def _draw(self, seed: int) -> dict:
        """TLE fields from the seed; orbits that dip into the atmosphere or that SGP4 rejects are redrawn."""
        rg, rng = self.template["ranges"], np.random.default_rng(seed)
        for _ in range(MAX_DRAWS):
            p = {
                "day": round(float(rng.uniform(*rg["day_of_year"])), 8),
                "mean_motion_rev_day": round(float(rng.uniform(*rg["mean_motion_rev_day"])), 8),
                "ecc": round(float(rng.uniform(*rg["ecc"])), 7),
                "bstar_mantissa": int(rng.integers(rg["bstar_mantissa"][0], rg["bstar_mantissa"][1] + 1)),
                "bstar_exponent": int(rng.integers(rg["bstar_exponent"][0], rg["bstar_exponent"][1] + 1)),
                "minutes": round(float(rng.uniform(*rg["minutes_after_epoch"])), 1),
                **{k: round(float(rng.uniform(*rg[k])), 4) for k in ("inc_deg", "raan_deg", "aop_deg")},
                "mean_anomaly_deg": round(float(rng.uniform(*rg["mean_anomaly_deg"])), 4),
            }
            n = p["mean_motion_rev_day"] * 2.0 * np.pi / 86400.0
            sma = (EARTH_MU_KM3_S2 / n ** 2) ** (1.0 / 3.0)
            if sma * (1.0 - p["ecc"]) < self.template["min_periapsis_km"]:
                continue
            p["satnum"], p["element_set"], p["rev_number"] = 70000 + seed % 29999, 999, int(rng.integers(1, 90000))
            try:
                sgp4_state(*self._lines(p), p["minutes"])
            except ValueError:
                continue
            return p
        raise RuntimeError(f"no valid draw in {MAX_DRAWS} tries for seed {seed}")

    @staticmethod
    def _lines(p: dict) -> tuple:
        return build_tle(satnum=p["satnum"], year=YEAR, day=p["day"], bstar_mantissa=p["bstar_mantissa"],
                         bstar_exponent=p["bstar_exponent"], element_set=p["element_set"], inc_deg=p["inc_deg"],
                         raan_deg=p["raan_deg"], ecc=p["ecc"], aop_deg=p["aop_deg"],
                         mean_anomaly_deg=p["mean_anomaly_deg"], mean_motion_rev_day=p["mean_motion_rev_day"],
                         rev_number=p["rev_number"])

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "values":
            raise ValueError("tle_state is answered with values only")
        tpl, p = self.template, self._draw(seed)
        line1, line2 = self._lines(p)
        tol = tpl["tolerance"]
        epoch = add_seconds(tpl["epoch"], (p["day"] - 1.0) * 86400.0)
        final_epoch = add_seconds(epoch, p["minutes"] * 60.0)
        fields = dict(tle=f"{line1}{LINE_BREAK}{line2}", minutes=p["minutes"], pos_tol=tol["position_km"],
                      vel_tol=tol["velocity_km_s"])
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields).replace(LINE_BREAK, "\n"),
                                 fill(tpl["statement"]["values"], fields), answer_format(mode, SATELLITE, KEYS)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=epoch, final_epoch=final_epoch, satellite=SATELLITE,
            initial_state={"type": "tle", "line1": line1, "line2": line2},
            tolerances={k: tol["position_km"] if k.endswith("_km") else tol["velocity_km_s"] for k in KEYS},
            params={**p, "line1": line1, "line2": line2})

    def reference_values(self, instance: Instance) -> dict:
        p = instance.params
        pos, vel = sgp4_state(p["line1"], p["line2"], p["minutes"])
        return dict(zip(KEYS, [float(c) for c in (*pos, *vel)]))

    def reference(self, instance: Instance) -> FinalAnswer:
        return FinalAnswer(schema_version="1.0", status="solved", values=self.reference_values(instance),
                           claims=Claims(verified=True, method="sgp4"))
