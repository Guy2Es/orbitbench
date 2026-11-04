# tests/test_training_families.py
"""The analytical training families (tsiolkovsky, escape_velocity): reference formulas, generator, grading."""
import math

import pytest

from orbitbench.answer import render_reply
from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.reference.tsiolkovsky import escape_delta_v_m_s, propellant_kg

NAMES = ("tsiolkovsky", "escape_velocity")
SEEDS = range(40)


def test_rocket_equation_textbook_value():
    # 1000 kg, Isp 300 s, dv = Isp g0 ln 2 burns exactly half of the mass.
    dv = 300.0 * 9.80665 * math.log(2.0)
    assert propellant_kg(1000.0, dv, 300.0) == pytest.approx(500.0)


def test_no_burn_no_propellant():
    assert propellant_kg(1500.0, 0.0, 320.0) == 0.0


def test_escape_burn_from_low_earth_orbit():
    # 7000 km: v_circ = 7.5459 km/s, escape needs 0.41421 of it = 3125.6 m/s.
    assert escape_delta_v_m_s(7000.0, EARTH_MU_KM3_S2) == pytest.approx(3125.6, abs=0.5)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_answer_is_graded_solved(name, seed):
    inst = generate(name, seed, "values")
    assert grade(inst, render_reply(FAMILIES[name].reference(inst))).outcome is Outcome.SOLVED


@pytest.mark.parametrize("name", NAMES)
def test_a_wrong_value_is_a_mismatch(name):
    inst = generate(name, 3, "values")
    key = next(iter(inst.tolerances))
    wrong = FAMILIES[name].reference(inst).model_copy(update={"values": {key: FAMILIES[name].reference_values(inst)[key] * 1.05}})
    assert grade(inst, render_reply(wrong)).outcome is Outcome.VALUES_MISMATCH


@pytest.mark.parametrize("name", NAMES)
def test_instances_are_deterministic_and_seeds_differ(name):
    assert generate(name, 7, "values") == generate(name, 7, "values")
    assert generate(name, 7, "values").params != generate(name, 8, "values").params


@pytest.mark.parametrize("name", NAMES)
def test_only_values_mode(name):
    with pytest.raises(ValueError):
        generate(name, 0, "maneuvers")


@pytest.mark.parametrize("name", NAMES)
def test_the_statement_names_the_answer_field_and_its_unit(name):
    inst = generate(name, 0, "values")
    key = next(iter(inst.tolerances))
    assert f"values.{key}" in inst.statement and "<final_answer>" in inst.statement
