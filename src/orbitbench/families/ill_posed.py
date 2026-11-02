# src/orbitbench/families/ill_posed.py
"""Statements that cannot be answered as written, and their well-posed twins.

Each trap is built from the same drawn numbers as its twin; a single detail separates them (a radius below the
Earth's, a missing specific impulse, a distance that is either an altitude or a radius). The right answer to a trap is
`status: ill_posed` with no value; the right answer to its twin is the number."""
import math

import numpy as np

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import EARTH_MU_KM3_S2, EARTH_RADIUS_KM, SATELLITE
from orbitbench.families.base import Family, Instance, answer_format
from orbitbench.reference.hohmann import hohmann

G0_M_S2 = 9.80665
KINDS = ("radius", "isp", "altitude")
ORBIT_NOTE = ("Physical model, which applies to every number you give: the Earth is a point mass with "
              f"mu = {EARTH_MU_KM3_S2} km^3/s^2 and equatorial radius {EARTH_RADIUS_KM} km, and nothing else acts on "
              "the spacecraft. Distances are in km, velocities in km/s, masses in kg and times in s, unless a field "
              "name says otherwise.")


class IllPosedFamily(Family):
    """One trap kind, as the trap (`well_posed=False`) or as its twin (`well_posed=True`)."""

    def __init__(self, kind: str, well_posed: bool):
        assert kind in KINDS
        self.kind, self.well_posed = kind, well_posed
        self.name = f"trap_{kind}" + ("_twin" if well_posed else "")

    def _draw(self, seed: int) -> dict:
        """The same numbers for a trap and its twin."""
        rng = np.random.default_rng(seed)
        r1 = round(float(rng.uniform(6700.0, 8000.0)), 1)
        r2 = round(float(rng.uniform(12000.0, 30000.0)), 1)
        p = {"r1_km": r1, "r2_km": r2, "inc_deg": round(float(rng.uniform(0.0, 98.0)), 1)}
        p["below_surface_km"] = round(float(rng.uniform(4500.0, 6000.0)), 1)      # radius trap: a radius under the Earth's
        p["mass_kg"] = round(float(rng.uniform(800.0, 3000.0)), 0)                 # isp kind
        p["isp_s"] = round(float(rng.uniform(250.0, 450.0)), 0)
        return p

    def _target_km(self, p: dict) -> float:
        """The radius of the radius kind: the twin's, or a trap radius below the Earth's surface."""
        return p["r2_km"] if self.well_posed else p["below_surface_km"]

    def _task(self, p: dict) -> tuple:
        """(statement paragraph, answer field, exact value or None, tolerance)."""
        r1, r2 = p["r1_km"], p["r2_km"]
        if self.kind == "radius":
            total = hohmann(r1, r2).total_m_s
            task = (f"Task: a spacecraft named {SATELLITE} is on a circular Earth orbit of radius {r1} km. Transfer it "
                    f"to a circular, coplanar orbit of radius {self._target_km(p)} km with a two-impulse Hohmann "
                    "transfer. Give the total delta-v, in m/s, in the field values.delta_v_total_m_s. It is correct "
                    "if it is within 1.0 m/s of the exact value.")
            return task, "delta_v_total_m_s", total, 1.0
        if self.kind == "isp":
            total = hohmann(r1, r2).total_m_s
            mass = p["mass_kg"] * (1.0 - math.exp(-total / (G0_M_S2 * p["isp_s"])))
            engine = (f"Its engine has a specific impulse of {p['isp_s']} s, with g0 = {G0_M_S2} m/s^2. "
                      if self.well_posed else "")
            task = (f"Task: a spacecraft named {SATELLITE} of {p['mass_kg']} kg, propellant included, is on a "
                    f"circular Earth orbit of radius {r1} km. {engine}It is transferred to a circular, coplanar orbit "
                    f"of radius {r2} km with a two-impulse Hohmann transfer. Give the propellant mass the transfer "
                    "consumes, in kg, in the field values.propellant_kg. It is correct if it is within "
                    f"{round(0.002 * mass, 1)} kg of the exact value.")
            return task, "propellant_kg", mass, round(0.002 * mass, 1)
        # the trap gives the same number as a distance that is either a radius or an altitude: two different answers
        target = f"a circular, coplanar orbit {'of radius' if self.well_posed else 'at'} {r2} km"
        total = hohmann(r1, r2).total_m_s
        task = (f"Task: a spacecraft named {SATELLITE} is on a circular Earth orbit of radius {r1} km. Transfer it to "
                f"{target} with a two-impulse Hohmann transfer. Give the total delta-v, in m/s, in the field "
                "values.delta_v_total_m_s. It is correct if it is within 1.0 m/s of the exact value.")
        return task, "delta_v_total_m_s", total, 1.0

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "values":
            raise ValueError("the trap families are answered with values only")
        p = self._draw(seed)
        task, field, value, tol = self._task(p)
        statement = "\n\n".join([ORBIT_NOTE, task, answer_format("values", SATELLITE, (field,))])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=2, statement=statement,
            epoch="01 Jan 2026 00:00:00.000", final_epoch="01 Jan 2026 00:00:00.000", satellite=SATELLITE,
            initial_state={"type": "keplerian", "sma_km": p["r1_km"], "ecc": 0.0, "inc_deg": p["inc_deg"],
                           "raan_deg": 0.0, "aop_deg": 0.0, "ta_deg": 0.0},
            tolerances={field: tol} if self.well_posed else {}, params={**p, "kind": self.kind, "exact": value},
            well_posed=self.well_posed)

    def reference(self, instance: Instance) -> FinalAnswer:
        if not self.well_posed:
            return FinalAnswer(schema_version="1.0", status="ill_posed",
                               reason=f"the {self.kind} statement cannot be answered as written",
                               claims=Claims(verified=True, method="reading"))
        field = next(iter(instance.tolerances))
        return FinalAnswer(schema_version="1.0", status="solved", values={field: instance.params["exact"]},
                           claims=Claims(verified=True, method="closed_form"))

    def reference_values(self, instance: Instance) -> dict:
        return {k: instance.params["exact"] for k in instance.tolerances}
