# tests/test_sun_synchronous.py
"""The sun_synchronous family: statement, the two references, the orbit replay plumbing and the grading, without GMAT."""
import pytest

from orbitbench.answer import FinalAnswer, render_reply
from orbitbench.constants import SUN_RATE_DEG_DAY
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.reference.sun_synchronous import inclination_formula, measured_drift_deg_day
from orbitbench.replay import PlanError, Replay, build_mission, orbit_instance

SEEDS = range(4)


def instance(seed=0):
    return generate("sun_synchronous", seed, "orbit")


def fake_replay(drift):
    return lambda inst, answer, job_dir: Replay(True, "ok", None, {"raan_drift_deg_day": drift}, 0.0)


def test_an_instance_is_an_orbit_to_design_at_level_four():
    inst = instance()
    assert (inst.mode, inst.level, inst.family) == ("orbit", 4, "sun_synchronous")
    assert "initial_orbit" in inst.statement and "0.985647" in inst.statement
    assert "inclination" in inst.statement and "inc_deg" not in inst.initial_state
    assert instance().statement == inst.statement and instance(1).statement != inst.statement


def test_only_the_orbit_mode_exists():
    with pytest.raises(ValueError):
        generate("sun_synchronous", 0, "values")


@pytest.mark.parametrize("seed", SEEDS)
def test_the_formula_is_a_sound_guess_that_the_tolerance_rejects(seed):
    inst = instance(seed)
    family, p = FAMILIES["sun_synchronous"], inst.params
    tol = inst.constraints[0]["abs_tol"]
    numeric, formula = family.reference_inclination(inst), family.reference_formula(inst)
    assert formula == pytest.approx(inclination_formula(p["sma_km"], p["ecc"]))
    assert abs(numeric - formula) < 0.25                    # the osculating start differs from the mean elements
    drift = measured_drift_deg_day(p["sma_km"], p["ecc"], formula, p["raan_deg"], p["aop_deg"], p["ta_deg"],
                                   p["n_orbits"])
    assert 2 * tol <= abs(drift - SUN_RATE_DEG_DAY) <= 0.015   # the closed form is close, and not enough
    exact = measured_drift_deg_day(p["sma_km"], p["ecc"], numeric, p["raan_deg"], p["aop_deg"], p["ta_deg"],
                                   p["n_orbits"])
    assert exact == pytest.approx(SUN_RATE_DEG_DAY, abs=1e-6)


def test_the_orbit_of_the_answer_is_flown_without_maneuvers():
    inst = instance()
    answer = FinalAnswer(schema_version="1.0", status="solved", initial_orbit={"inc_deg": 98.2})
    mission = build_mission(orbit_instance(inst, answer), answer)
    assert mission["spacecraft"][0]["state"]["inc_deg"] == 98.2
    assert [step["type"] for step in mission["sequence"]] == ["propagate"]
    assert mission["force_models"][0]["gravity"] == {"degree": 2, "order": 0, "file": "JGM3"}


@pytest.mark.parametrize("bad", [None, "98", True, -1.0, 181.0])
def test_a_bad_inclination_is_refused_before_replay(bad):
    answer = FinalAnswer(schema_version="1.0", status="solved", initial_orbit={"inc_deg": bad})
    with pytest.raises(PlanError):
        orbit_instance(instance(), answer)


def test_grading_follows_the_measured_drift():
    inst = instance()
    reply = render_reply(FAMILIES["sun_synchronous"].reference(inst))
    assert grade(inst, reply, replay_fn=fake_replay(SUN_RATE_DEG_DAY)).outcome is Outcome.SOLVED
    off = grade(inst, reply, replay_fn=fake_replay(SUN_RATE_DEG_DAY + 0.05))
    assert off.outcome is Outcome.CONSTRAINTS_VIOLATED and off.reward < 1.0


def test_a_reply_without_an_inclination_is_a_format_failure():
    inst = instance()
    reply = render_reply(FinalAnswer(schema_version="1.0", status="solved", initial_orbit={"raan_deg": 3.0}))
    result = grade(inst, reply, replay_fn=fake_replay(SUN_RATE_DEG_DAY))
    assert result.outcome is Outcome.INVALID_FORMAT and result.detail["missing"] == ["initial_orbit.inc_deg"]
