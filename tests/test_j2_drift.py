# tests/test_j2_drift.py
"""The j2_drift family: numerical J2 reference, instance generator, statement, grading."""
import math

import numpy as np
import pytest

from orbitbench.answer import render_reply
from orbitbench.constants import EARTH_J2, EARTH_MU_KM3_S2, EARTH_RADIUS_KM
from orbitbench.families import FAMILIES, generate
from orbitbench.families.j2_drift import ELEMENTS, KEYS
from orbitbench.grader import Outcome, grade
from orbitbench.reference.j2 import acceleration, elements_from_state
from orbitbench.reference.kepler import state_from_elements

FAMILY = FAMILIES["j2_drift"]
SEEDS = range(40)


def instance(seed):
    return generate("j2_drift", seed, "values")


def wrapped(a, b):
    return abs(math.remainder(a - b, 360.0))


def test_the_elements_read_from_a_state_are_those_it_was_built_from():
    el = dict(sma_km=9000.0, ecc=0.2, inc_deg=63.0, raan_deg=100.0, aop_deg=250.0, ta_deg=40.0)
    got = elements_from_state(*state_from_elements(*el.values()))
    for k in ("sma_km", "ecc", "inc_deg", "raan_deg", "aop_deg"):
        assert got[k] == pytest.approx(el[k], abs=1e-9)


def test_without_j2_the_integration_is_the_kepler_orbit():
    from orbitbench.reference.kepler import propagate
    el = (8000.0, 0.1, 40.0, 50.0, 60.0, 70.0)
    ref = propagate(*el, 20000.0)
    pos0, vel0 = state_from_elements(*el)
    from scipy.integrate import solve_ivp
    sol = solve_ivp(lambda _, y: np.concatenate([y[3:], acceleration(y[:3], j2=0.0)]), (0, 20000.0),
                    np.concatenate([pos0, vel0]), method="DOP853", rtol=1e-13, atol=1e-10)
    assert np.allclose(sol.y[:3, -1], ref[0], atol=1e-6)


def test_the_j2_acceleration_matches_the_potential_gradient():
    pos = np.array([5000.0, -4000.0, 3000.0])
    pot = lambda p: -EARTH_MU_KM3_S2 / np.linalg.norm(p) * (
        1.0 - 0.5 * EARTH_J2 * (EARTH_RADIUS_KM / np.linalg.norm(p)) ** 2 * (3.0 * p[2] ** 2 / (p @ p) - 1.0))
    h = 1e-3
    grad = np.array([(pot(pos + h * e) - pot(pos - h * e)) / (2 * h) for e in np.eye(3)])
    assert np.allclose(acceleration(pos), -grad, rtol=1e-6)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_node_drift_has_the_sign_and_size_of_the_secular_formula(seed):
    inst = instance(seed)
    p = inst.params
    ref = FAMILY.reference_values(inst)
    a, e, inc = p["sma_km"], p["ecc"], math.radians(p["inc_deg"])
    n = math.sqrt(EARTH_MU_KM3_S2 / a**3)
    rate = -1.5 * n * EARTH_J2 * (EARTH_RADIUS_KM / (a * (1 - e * e))) ** 2 * math.cos(inc)
    secular = (p["raan_deg"] + math.degrees(rate) * p["dt_days"] * 86400) % 360
    assert wrapped(secular, ref["raan_deg"]) < 0.1   # periodic terms and the mean/osculating gap


def test_instances_are_deterministic_and_seeds_differ():
    assert instance(7) == instance(7)
    assert instance(7).params != instance(8).params


@pytest.mark.parametrize("seed", SEEDS)
def test_draws_respect_the_template(seed):
    tpl = FAMILY.template
    inst = instance(seed)
    p, ref = inst.params, FAMILY.reference_values(inst)
    for k in ELEMENTS:
        assert tpl["ranges"][k][0] <= p[k] <= tpl["ranges"][k][1]
    assert p["sma_km"] * (1 - p["ecc"]) >= tpl["min_periapsis_km"]
    for k in KEYS:
        assert min(ref[k], 360.0 - ref[k]) >= tpl["wrap_margin_deg"]
    assert wrapped(ref["raan_deg"], p["raan_deg"]) >= tpl["min_node_drift_deg"]
    assert inst.gravity == {"degree": 2, "order": 0, "file": "JGM3"}


def test_only_the_values_mode_exists():
    with pytest.raises(ValueError):
        generate("j2_drift", 0, "maneuvers")


def test_statement_gives_the_constants_the_frame_and_the_dates():
    inst = instance(5)
    p = inst.params
    for fragment in (str(p["sma_km"]), str(p["ecc"]), "398600.4415", "6378.1363", "1.0826266906e-03", inst.epoch,
                     inst.final_epoch, f"{p['dt_days']} days", "z axis", "values.raan_deg", "values.aop_deg",
                     "<final_answer>"):
        assert fragment in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]


def test_the_reference_is_solved_and_a_wrong_sign_is_not():
    inst = instance(4)
    ref = FAMILY.reference(inst)
    assert grade(inst, render_reply(ref)).outcome is Outcome.SOLVED
    drift = math.remainder(ref.values["raan_deg"] - inst.params["raan_deg"], 360.0)
    flipped = (inst.params["raan_deg"] - drift) % 360.0
    wrong = ref.model_copy(update={"values": {**ref.values, "raan_deg": flipped}})
    assert grade(inst, render_reply(wrong)).outcome is Outcome.VALUES_MISMATCH


@pytest.mark.parametrize("seed", range(10))
def test_a_one_percent_error_on_the_drift_fails(seed):
    inst = instance(seed)
    ref = FAMILY.reference(inst)
    drift = math.remainder(ref.values["raan_deg"] - inst.params["raan_deg"], 360.0)
    wrong = ref.model_copy(update={"values": {**ref.values, "raan_deg": (inst.params["raan_deg"] + 1.01 * drift) % 360.0}})
    assert grade(inst, render_reply(wrong)).outcome is Outcome.VALUES_MISMATCH


def test_the_unperturbed_orbit_is_caught():
    inst = instance(6)
    p = inst.params
    wrong = FAMILY.reference(inst).model_copy(update={"values": {"raan_deg": p["raan_deg"], "aop_deg": p["aop_deg"]}})
    assert grade(inst, render_reply(wrong)).outcome is Outcome.VALUES_MISMATCH


def test_a_missing_field_is_a_format_failure():
    inst = instance(4)
    ref = FAMILY.reference(inst)
    only = ref.model_copy(update={"values": {"raan_deg": ref.values["raan_deg"]}})
    assert grade(inst, render_reply(only)).outcome is Outcome.INVALID_FORMAT
