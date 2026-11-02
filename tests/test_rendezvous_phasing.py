# tests/test_rendezvous_phasing.py
"""The rendezvous_phasing family: statement, the two references, the miss constraints and the grading, without GMAT."""
import pytest

from orbitbench.answer import render_reply
from orbitbench.epoch import parse_epoch
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, check_constraints, grade
from orbitbench.reference.rendezvous import best_phasing, circular_period_s, plan_miss
from orbitbench.replay import Replay, build_mission

SEEDS = range(10)


def instance(seed=0):
    return generate("rendezvous_phasing", seed, "maneuvers")


def burns_of(inst, answer):
    start = parse_epoch(inst.epoch)
    return [((parse_epoch(m.epoch_utc) - start) / 1000.0, m.delta_v_km_s[0]) for m in answer.maneuvers]


def final_state_of(inst, pos, vel):
    return {"position_km": pos, "velocity_km_s": vel}


def test_an_instance_is_a_level_four_maneuver_plan():
    inst = instance()
    assert (inst.mode, inst.level, inst.family) == ("maneuvers", 4, "rendezvous_phasing")
    assert "ahead" in inst.statement and "final_answer" in inst.statement
    assert instance().statement == inst.statement and instance(1).statement != inst.statement


def test_only_the_maneuver_mode_exists():
    with pytest.raises(ValueError):
        generate("rendezvous_phasing", 0, "values")


@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_plan_meets_the_target_when_integrated(seed):
    inst, p = instance(seed), instance(seed).params
    answer = FAMILIES["rendezvous_phasing"].reference(inst)
    miss_km, miss_m_s = plan_miss(p["sma_km"], p["inc_deg"], p["raan_deg"], p["ta_deg"], p["target_ta_deg"],
                                  burns_of(inst, answer), p["duration_s"])
    assert miss_km < 0.1 and miss_m_s < 0.1


@pytest.mark.parametrize("seed", SEEDS)
def test_the_budget_is_the_optimum_plus_the_margin_and_the_orbit_stays_high(seed):
    inst, p = instance(seed), instance(seed).params
    family = FAMILIES["rendezvous_phasing"]
    best = best_phasing(p["sma_km"], p["duration_s"], family.template["min_radius_km"])
    assert best.low_radius_km >= family.template["min_radius_km"]
    assert family.reference_delta_v_m_s(inst) == pytest.approx(best.total_m_s)
    assert p["budget_m_s"] == pytest.approx(best.total_m_s + family.template["dv_margin_m_s"], abs=0.06)
    assert p["duration_s"] < 2.0 * circular_period_s(p["sma_km"])


def test_a_wrong_plan_misses_the_target():
    inst, p = instance(), instance().params
    answer = FAMILIES["rendezvous_phasing"].reference(inst)
    early = [(t - 60.0 if t else t, dv) for t, dv in burns_of(inst, answer)]    # the second burn, a minute early
    miss_km, miss_m_s = plan_miss(p["sma_km"], p["inc_deg"], p["raan_deg"], p["ta_deg"], p["target_ta_deg"], early,
                                  p["duration_s"])
    tol = FAMILIES["rendezvous_phasing"].template["tolerance"]
    assert miss_km > tol["position_km"] and miss_m_s > tol["velocity_m_s"]


def test_the_miss_constraints_follow_the_replayed_state():
    inst = instance()
    point = {c["quantity"]: c["point"] for c in inst.constraints if "point" in c}
    on_target = final_state_of(inst, point["position_error_km"], point["velocity_error_m_s"])
    assert all(c["met"] for c in check_constraints(inst, on_target, 0.0))
    near = [x + 3.0 for x in point["position_error_km"]]
    checks = check_constraints(inst, final_state_of(inst, near, point["velocity_error_m_s"]), 0.0)
    assert [c["met"] for c in checks] == [False, True, True]


def test_the_reference_plan_is_two_velocity_burns_on_the_dates_of_the_statement():
    inst = instance()
    mission = build_mission(inst, FAMILIES["rendezvous_phasing"].reference(inst))
    assert [step["type"] for step in mission["sequence"]] == ["impulsive_burn", "propagate", "impulsive_burn"]
    assert inst.final_epoch in inst.statement and mission["sequence"][1]["stop"]["epoch"] == inst.final_epoch


def test_grading_follows_the_replayed_state():
    inst = instance()
    reference = FAMILIES["rendezvous_phasing"].reference(inst)
    point = {c["quantity"]: c["point"] for c in inst.constraints if "point" in c}
    state = final_state_of(inst, point["position_error_km"], point["velocity_error_m_s"])
    dv = FAMILIES["rendezvous_phasing"].reference_delta_v_m_s(inst)

    def fake(state):
        return lambda i, a, d: Replay(True, "ok", None, state, dv)

    assert grade(inst, render_reply(reference), replay_fn=fake(state)).outcome is Outcome.SOLVED
    missed = final_state_of(inst, [x + 50.0 for x in point["position_error_km"]], point["velocity_error_m_s"])
    off = grade(inst, render_reply(reference), replay_fn=fake(missed))
    assert off.outcome is Outcome.CONSTRAINTS_VIOLATED and 0.0 < off.reward < 1.0
