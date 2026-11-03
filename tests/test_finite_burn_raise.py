# tests/test_finite_burn_raise.py
"""The finite-burn family and the replay of finite burns, without GMAT."""
import pytest

from orbitbench.answer import FinalAnswer, FiniteBurn, Maneuver, extract_answer, render_reply
from orbitbench.epoch import add_seconds
from orbitbench.families import FAMILIES, generate
from orbitbench.epoch import parse_epoch
from orbitbench.reference.finite_burn import apoapsis_after, circularization, impulsive_duration_s
from orbitbench.replay import PlanError, build_mission

SEEDS = range(6)


def instance(seed=0):
    return generate("finite_burn_raise", seed, "finite")


def plan(inst, *burns, maneuvers=()):
    return FinalAnswer(schema_version="1.0", status="solved", finite_burns=list(burns), maneuvers=list(maneuvers))


def burn(inst, start=0.0, duration=100.0, direction="prograde"):
    return FiniteBurn(epoch_utc=add_seconds(inst.epoch, start), spacecraft=inst.satellite, duration_s=duration,
                      direction=direction)


def test_an_instance_is_a_level_four_finite_burn_task():
    inst = instance()
    assert (inst.mode, inst.level, inst.family) == ("finite", 4, "finite_burn_raise")
    assert "finite_burns" in inst.statement and "duration_s" in inst.statement
    assert inst.propulsion["thrusters"][0]["thrust_n"] == inst.params["thrust_n"]
    assert instance().statement == inst.statement and instance(1).statement != inst.statement


@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_burn_reaches_the_apoapsis_and_the_impulsive_guess_does_not(seed):
    inst, p = instance(seed), instance(seed).params
    mass = FAMILIES["finite_burn_raise"]._mass_kg()
    assert abs(apoapsis_after(p["r1_km"], p["thrust_n"], p["isp_s"], mass, p["duration_s"]) - p["ra_km"]) < 1.0
    guess = impulsive_duration_s(p["r1_km"], p["ra_km"], p["thrust_n"], p["isp_s"], mass)
    assert abs(apoapsis_after(p["r1_km"], p["thrust_n"], p["isp_s"], mass, guess) - p["ra_km"]) > 0.003 * p["ra_km"]
    second = circularization(p["r1_km"], p["ra_km"], p["thrust_n"], p["isp_s"], mass, p["duration_s"])
    assert second["worst_miss"] < 0.006   # inside half the tolerance
    assert p["coast_s"] == pytest.approx(second["coast_s"], abs=1e-3)
    assert p["duration_s"] + p["coast_s"] + p["duration2_s"] < (
        parse_epoch(inst.final_epoch) - parse_epoch(inst.epoch)) / 1000.0     # both burns fit before the final epoch


def test_the_reference_plan_is_two_finite_burns_with_the_thruster_of_the_spacecraft():
    inst = instance()
    mission = build_mission(inst, FAMILIES["finite_burn_raise"].reference(inst))
    assert [step["type"] for step in mission["sequence"]] == ["finite_burn", "propagate", "finite_burn", "propagate"]
    assert mission["sequence"][0]["thruster"] == "Thr" and mission["sequence"][0]["direction"] == "prograde"
    sc = mission["spacecraft"][0]
    assert sc["dry_mass_kg"] == 850.0 and sc["tanks"][0]["fuel_mass_kg"] == 600.0
    assert [c["quantity"] for c in inst.constraints] == ["ra_km", "rp_km", "inc_deg"]


def test_burns_are_ordered_by_date_whatever_the_list_they_come_in():
    inst = instance()
    impulsive = Maneuver(epoch_utc=add_seconds(inst.epoch, 10.0), spacecraft=inst.satellite, frame="VNB",
                         delta_v_km_s=[0.0, 0.0, 0.0])
    mission = build_mission(inst, plan(inst, burn(inst, 100.0, 200.0), maneuvers=[impulsive]))
    assert [s["type"] for s in mission["sequence"]] == ["propagate", "impulsive_burn", "propagate", "finite_burn",
                                                        "propagate"]


@pytest.mark.parametrize("make, message", [
    (lambda i: plan(i, burn(i, 0.0, 500.0), burn(i, 100.0, 50.0)), "before the end"),
    (lambda i: plan(i, burn(i, 0.0, 1e6)), "ends after the final epoch"),
    (lambda i: plan(i, FiniteBurn(epoch_utc=i.epoch, spacecraft="Other", duration_s=1.0)), "not 'Other'")])
def test_plans_that_cannot_be_flown_are_refused(make, message):
    inst = instance()
    with pytest.raises(PlanError, match=message):
        build_mission(inst, make(inst))


def test_finite_burns_need_a_spacecraft_with_a_thruster():
    hohmann = generate("hohmann", 0, "maneuvers")
    with pytest.raises(PlanError, match="no thruster"):
        build_mission(hohmann, plan(hohmann, burn(hohmann)))


def test_the_new_fields_round_trip_and_the_old_replies_still_parse():
    inst = instance()
    reference = FAMILIES["finite_burn_raise"].reference(inst)
    assert extract_answer(render_reply(reference)) == reference
    old = '<final_answer>{"schema_version": "1.0", "status": "solved", "maneuvers": []}</final_answer>'
    assert extract_answer(old).finite_burns == []
    with pytest.raises(Exception):
        FiniteBurn(epoch_utc=inst.epoch, spacecraft="Sat", duration_s=-1.0)
    with pytest.raises(Exception):
        FiniteBurn(epoch_utc=inst.epoch, spacecraft="Sat", duration_s=1.0, direction="sideways")
