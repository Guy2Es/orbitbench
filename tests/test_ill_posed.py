# tests/test_ill_posed.py
"""The trap families and their twins: same numbers, one detail apart, and a grader that rewards the right status."""
import pytest

from orbitbench.answer import FinalAnswer, render_reply
from orbitbench.constants import EARTH_RADIUS_KM
from orbitbench.families import FAMILIES, generate
from orbitbench.families.ill_posed import KINDS
from orbitbench.grader import Outcome, grade
from orbitbench.reference.hohmann import hohmann

SEEDS = range(4)


def pair(kind, seed=0):
    return generate(f"trap_{kind}", seed, "values"), generate(f"trap_{kind}_twin", seed, "values")


@pytest.mark.parametrize("kind", KINDS)
def test_a_trap_and_its_twin_share_their_numbers_and_differ_by_one_detail(kind):
    trap, twin = pair(kind)
    assert (trap.well_posed, twin.well_posed) == (False, True)
    shared = {k: v for k, v in trap.params.items() if k not in ("exact",)}
    assert shared == {k: v for k, v in twin.params.items() if k != "exact"}
    assert trap.statement != twin.statement and trap.level == twin.level == 2
    assert pair(kind)[0].statement == trap.statement


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("seed", SEEDS)
def test_the_right_answer_to_a_trap_is_ill_posed_and_to_its_twin_the_number(kind, seed):
    trap, twin = pair(kind, seed)
    assert grade(trap, render_reply(FAMILIES[trap.family].reference(trap))).outcome is Outcome.SOLVED
    assert grade(twin, render_reply(FAMILIES[twin.family].reference(twin))).outcome is Outcome.SOLVED


@pytest.mark.parametrize("kind", KINDS)
def test_a_number_for_a_trap_is_a_missed_trap_and_ill_posed_for_a_twin_a_false_alarm(kind):
    trap, twin = pair(kind)
    number = FAMILIES[twin.family].reference(twin)
    assert grade(trap, render_reply(number)).outcome is Outcome.MISSED_TRAP
    alarm = FinalAnswer(schema_version="1.0", status="ill_posed", reason="not enough data")
    assert grade(twin, render_reply(alarm)).outcome is Outcome.WRONG_STATUS


def test_an_ill_posed_status_that_still_gives_a_value_does_not_pass_the_trap():
    trap, twin = pair("radius")
    hedged = FinalAnswer(schema_version="1.0", status="ill_posed", reason="below the surface", values={"x": 1.0})
    assert grade(trap, render_reply(hedged)).outcome is Outcome.MISSED_TRAP


def test_the_radius_trap_is_below_the_earth_and_the_twin_is_not():
    trap, twin = pair("radius")
    assert trap.params["below_surface_km"] < EARTH_RADIUS_KM < twin.params["r2_km"]
    assert str(trap.params["below_surface_km"]) in trap.statement and str(EARTH_RADIUS_KM) in trap.statement


def test_the_isp_trap_has_no_specific_impulse_and_the_twin_has_one():
    trap, twin = pair("isp")
    assert "specific impulse" not in trap.statement and "specific impulse" in twin.statement
    p = twin.params
    assert p["exact"] < p["mass_kg"] and p["exact"] > 0.0


def test_the_two_readings_of_the_altitude_trap_give_different_answers():
    trap, _ = pair("altitude")
    p = trap.params
    as_radius = hohmann(p["r1_km"], p["r2_km"]).total_m_s
    as_altitude = hohmann(p["r1_km"], p["r2_km"] + EARTH_RADIUS_KM).total_m_s
    assert abs(as_radius - as_altitude) > 10.0 * 1.0
    assert "of radius" not in trap.statement.split("Transfer it to")[1]


def test_the_well_posed_default_leaves_the_existing_instances_unchanged():
    assert generate("hohmann", 0, "values").well_posed is True
