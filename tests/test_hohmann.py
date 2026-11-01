# tests/test_hohmann.py
"""The Hohmann family: reference formulas, instance generator, statement."""
import math

import pytest

from orbitbench.epoch import parse_epoch
from orbitbench.families import FAMILIES, generate
from orbitbench.reference.hohmann import hohmann

FAMILY = FAMILIES["hohmann"]
SEEDS = range(40)


def test_reference_matches_the_known_leo_to_geo_value():
    # 6778.137 -> 42164 km, computed separately in the E4 experiment: 3853.9570515 m/s.
    assert hohmann(6778.137, 42164.0).total_m_s == pytest.approx(3853.9570515, abs=1e-6)


def test_reference_burns_are_both_prograde_when_going_up():
    transfer = hohmann(7000.0, 20000.0)
    assert transfer.delta_v1_km_s > 0 and transfer.delta_v2_km_s > 0


def test_reference_is_symmetric_in_total_when_going_down():
    assert hohmann(20000.0, 7000.0).total_km_s == pytest.approx(hohmann(7000.0, 20000.0).total_km_s)


def test_reference_agrees_with_core_astro():
    pytest.importorskip("core")
    from core import astro
    for seed in range(10):
        p = generate("hohmann", seed, "values").params
        ours, theirs = hohmann(p["r1_km"], p["r2_km"]), astro.hohmann(p["r1_km"], p["r2_km"])
        assert ours.total_km_s == pytest.approx(theirs["delta_v_total_km_s"], abs=1e-9)
        assert ours.transfer_time_s == pytest.approx(theirs["transfer_time_sec"], abs=1e-6)


def test_instances_are_deterministic_and_seeds_differ():
    assert generate("hohmann", 7, "values") == generate("hohmann", 7, "values")
    assert generate("hohmann", 7, "values").params != generate("hohmann", 8, "values").params


def test_both_modes_share_the_orbit_of_a_seed():
    values, plan = generate("hohmann", 3, "values"), generate("hohmann", 3, "maneuvers")
    assert values.params == plan.params and values.initial_state == plan.initial_state
    assert (values.level, plan.level) == (1, 3)


@pytest.mark.parametrize("seed", SEEDS)
def test_draws_stay_in_the_template_ranges(seed):
    rg, tpl = FAMILY.template["ranges"], FAMILY.template
    p = generate("hohmann", seed, "values").params
    assert rg["r1_km"][0] <= p["r1_km"] <= rg["r1_km"][1] and rg["r2_km"][0] <= p["r2_km"] <= rg["r2_km"][1]
    assert rg["inc_deg"][0] <= p["inc_deg"] <= rg["inc_deg"][1]
    assert p["r2_km"] / p["r1_km"] >= tpl["min_radius_ratio"]


@pytest.mark.parametrize("seed", SEEDS)
def test_final_epoch_is_after_the_transfer(seed):
    inst = generate("hohmann", seed, "maneuvers")
    transfer = hohmann(inst.params["r1_km"], inst.params["r2_km"])
    gap_s = (parse_epoch(inst.final_epoch) - parse_epoch(inst.epoch)) / 1000
    assert gap_s == pytest.approx(transfer.transfer_time_s + FAMILY.template["final_margin_s"], abs=0.001)


def test_statement_fixes_what_the_answer_depends_on():
    inst = generate("hohmann", 5, "maneuvers")
    for fragment in (str(inst.params["r1_km"]), str(inst.params["r2_km"]), "398600.4415", inst.epoch,
                     inst.final_epoch, "point mass", "Prince-Dormand", "<final_answer>", "VNB", "millisecond"):
        assert fragment in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]   # no unfilled placeholder in the task text


def test_values_statement_states_the_unit_and_tolerance():
    statement = generate("hohmann", 5, "values").statement
    assert "m/s" in statement and "delta_v_total_m_s" in statement and "within 1.0 m/s" in statement


def test_reference_answers_carry_the_expected_fields():
    values = FAMILY.reference(generate("hohmann", 2, "values"))
    assert values.status == "solved" and not values.maneuvers and "delta_v_total_m_s" in values.values
    plan = FAMILY.reference(generate("hohmann", 2, "maneuvers"))
    assert len(plan.maneuvers) == 2 and plan.maneuvers[0].epoch_utc == generate("hohmann", 2, "maneuvers").epoch
    assert plan.values["delta_v_total_m_s"] == pytest.approx(
        1000 * sum(math.sqrt(sum(c * c for c in m.delta_v_km_s)) for m in plan.maneuvers))
