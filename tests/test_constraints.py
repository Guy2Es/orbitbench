# tests/test_constraints.py
"""Constraint kinds beyond the Hohmann ones, and constants shared with GMAT."""
import math
import os
from dataclasses import replace
from pathlib import Path

import pytest

from orbitbench.constants import EARTH_J2, EARTH_MU_KM3_S2, EARTH_RADIUS_KM
from orbitbench.families import generate
from orbitbench.grader import check_constraints

BASE = generate("hohmann", 1, "maneuvers")
FINAL = {"sma_km": 10000.0, "ecc": 0.2, "raan_deg": 359.9, "inc_deg": 51.0}


def met(constraint, plan_dv=0.0):
    inst = replace(BASE, constraints=[constraint])
    return check_constraints(inst, FINAL, plan_dv)[0]["met"]


def test_periapsis_and_apoapsis_are_derived_from_the_final_state():
    assert met({"quantity": "rp_km", "target": 8000.0, "abs_tol": 0.001})
    assert met({"quantity": "ra_km", "target": 12000.0, "abs_tol": 0.001})


def test_an_angle_gap_wraps_around_360():
    assert met({"quantity": "raan_deg", "target": 0.05, "abs_tol": 0.2, "periodic": 360})
    assert not met({"quantity": "raan_deg", "target": 0.05, "abs_tol": 0.2})


def test_a_delta_v_budget_bounds_the_plan_not_the_final_state():
    budget = {"quantity": "plan_delta_v_m_s", "max": 100.0}
    assert met(budget, plan_dv=99.0) and not met(budget, plan_dv=101.0)


def test_j2_is_the_value_stored_in_the_gmat_gravity_file():
    assert EARTH_J2 == pytest.approx(1.0826266906e-3, rel=1e-9)
    root = os.environ.get("GMAT_INSTALL", r"D:\Program Files (x86)\GMAT")
    cof = Path(root) / "data" / "gravity" / "earth" / "JGM3.cof"
    if not cof.exists():
        pytest.skip("GMAT is not installed")
    lines = cof.read_text().splitlines()
    header = next(line for line in lines if line.startswith("POTFIELD")).split()
    c20 = next(line for line in lines if line.startswith("RECOEF    2  0")).split()[3]
    assert float(header[4]) / 1e9 == pytest.approx(EARTH_MU_KM3_S2)
    assert float(header[5]) / 1e3 == pytest.approx(EARTH_RADIUS_KM)
    assert -float(c20) * math.sqrt(5.0) == pytest.approx(EARTH_J2, rel=1e-12)
