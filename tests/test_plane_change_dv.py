# tests/test_plane_change_dv.py
"""The plane-change family: reference formulas, instance generator, statement."""
import math

import pytest

from orbitbench.families import FAMILIES, generate
from orbitbench.reference.plane_change import plane_change

FAMILY = FAMILIES["plane_change_dv"]
SEEDS = range(40)


def test_reference_matches_the_textbook_value():
    # 7000 km circular, 28.5 deg: v = 7.5459 km/s, dv = 2 v sin(14.25 deg).
    v = math.sqrt(398600.4415 / 7000.0)
    assert plane_change(7000.0, 0.0, 28.5).total_m_s == pytest.approx(2000 * v * math.sin(math.radians(14.25)))


def test_raising_and_lowering_the_inclination_cost_the_same():
    assert plane_change(8000.0, 10.0, 40.0).total_m_s == pytest.approx(plane_change(8000.0, 40.0, 10.0).total_m_s)


def test_the_burn_components_have_the_norm_of_the_delta_v():
    c = plane_change(9000.0, 20.0, 55.0)
    assert math.hypot(c.along_velocity_km_s, c.along_normal_km_s) == pytest.approx(c.delta_v_km_s)


def test_a_plane_change_costs_more_on_a_low_orbit_than_on_a_high_one():
    assert plane_change(7000.0, 0.0, 30.0).total_m_s > plane_change(42164.0, 0.0, 30.0).total_m_s


def test_reference_agrees_with_core_astro():
    pytest.importorskip("core")
    from core import astro
    for seed in range(10):
        p = generate("plane_change_dv", seed, "values").params
        theirs = astro.plane_change(p["r_km"], abs(p["inc2_deg"] - p["inc1_deg"]))
        assert plane_change(p["r_km"], p["inc1_deg"], p["inc2_deg"]).delta_v_km_s == pytest.approx(
            theirs["pure_plane_change_dv_km_s"], rel=1e-6)


def test_instances_are_deterministic_and_seeds_differ():
    assert generate("plane_change_dv", 7, "values") == generate("plane_change_dv", 7, "values")
    assert generate("plane_change_dv", 7, "values").params != generate("plane_change_dv", 8, "values").params


@pytest.mark.parametrize("seed", SEEDS)
def test_draws_stay_in_the_template_ranges(seed):
    rg = FAMILY.template["ranges"]
    p = generate("plane_change_dv", seed, "values").params
    assert rg["r_km"][0] <= p["r_km"] <= rg["r_km"][1] and rg["inc1_deg"][0] <= p["inc1_deg"] <= rg["inc1_deg"][1]
    assert 0.0 <= p["inc2_deg"] <= 180.0
    assert abs(p["inc2_deg"] - p["inc1_deg"]) >= rg["delta_inc_deg"][0] - 0.1


def test_both_directions_occur():
    deltas = [p["inc2_deg"] - p["inc1_deg"] for p in (generate("plane_change_dv", s, "values").params for s in SEEDS)]
    assert any(d > 0 for d in deltas) and any(d < 0 for d in deltas)


def test_statement_fixes_what_the_answer_depends_on():
    inst = generate("plane_change_dv", 5, "values")
    for fragment in (str(inst.params["r_km"]), str(inst.params["inc1_deg"]), str(inst.params["inc2_deg"]),
                     "398600.4415", inst.epoch, "point mass", "m/s", "delta_v_total_m_s", "<final_answer>"):
        assert fragment in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]


def test_plan_statement_names_the_frame_axes_and_the_checks():
    statement = generate("plane_change_dv", 5, "maneuvers").statement
    for fragment in ("orbit normal", "Prince-Dormand", "millisecond", "inclination within"):
        assert fragment in statement


def test_reference_answers_carry_the_expected_fields():
    values = FAMILY.reference(generate("plane_change_dv", 2, "values"))
    assert values.status == "solved" and not values.maneuvers
    plan = FAMILY.reference(generate("plane_change_dv", 2, "maneuvers"))
    assert len(plan.maneuvers) == 1 and plan.maneuvers[0].frame == "VNB"
    assert plan.values["delta_v_total_m_s"] == pytest.approx(
        1000 * math.sqrt(sum(c * c for c in plan.maneuvers[0].delta_v_km_s)))
