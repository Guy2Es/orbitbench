# tests/test_hohmann_or_bielliptic_plan.py
"""The hohmann_or_bielliptic_plan family: bi-elliptic reference, strategy draw, statement."""
import math

import pytest

from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.epoch import parse_epoch
from orbitbench.families import FAMILIES, generate
from orbitbench.reference.bielliptic import best_bielliptic, bielliptic
from orbitbench.reference.hohmann import hohmann

FAMILY = FAMILIES["hohmann_or_bielliptic_plan"]
SEEDS = range(40)


def instance(seed):
    return generate("hohmann_or_bielliptic_plan", seed, "maneuvers")


def test_a_bielliptic_transfer_with_apoapsis_at_r2_is_the_hohmann_transfer():
    r1, r2 = 7000.0, 60000.0
    assert bielliptic(r1, r2, r2).total_m_s == pytest.approx(hohmann(r1, r2).total_m_s, rel=1e-12)


def test_the_classic_ratio_beyond_which_bielliptic_wins_is_11_94():
    r1 = 7000.0
    # Just beyond 11.94 the gain needs an apoapsis hundreds of times r2, so the bound is very loose here.
    for ratio, bielliptic_wins in ((11.5, False), (11.9, False), (12.5, True), (13.0, True)):
        r2 = ratio * r1
        gap = hohmann(r1, r2).total_m_s - best_bielliptic(r1, r2, 1000 * r2).total_m_s
        assert (gap > 1e-6) is bielliptic_wins, (ratio, gap)


def test_a_higher_apoapsis_cost_less_beyond_15_58():
    r1, r2 = 7000.0, 7000.0 * 20
    costs = [bielliptic(r1, r2, f * r2).total_m_s for f in (1.0, 2.0, 5.0, 20.0)]
    assert costs == sorted(costs, reverse=True)


def test_the_best_apoapsis_under_a_bound_is_found_by_a_scan_and_stays_inside_it():
    r1, r2, bound = 7000.0, 150000.0, 300000.0
    best = best_bielliptic(r1, r2, bound)
    assert r2 <= best.ra_km <= bound * (1 + 1e-9)
    for ra in (r2, 1.2 * r2, 1.7 * r2, bound):
        assert best.total_m_s <= bielliptic(r1, r2, ra).total_m_s + 1e-9


def test_burn_dates_follow_half_periods_of_the_two_ellipses():
    r1, r2, ra = 7000.0, 150000.0, 250000.0
    b = bielliptic(r1, r2, ra)
    half = lambda a: math.pi * math.sqrt(a**3 / EARTH_MU_KM3_S2)
    assert b.time_to_second_burn_s == pytest.approx(half((r1 + ra) / 2))
    assert b.time_to_third_burn_s == pytest.approx(half((r1 + ra) / 2) + half((ra + r2) / 2))


@pytest.mark.parametrize("seed", SEEDS)
def test_the_drawn_strategy_wins_by_a_clear_margin(seed):
    inst = instance(seed)
    p = inst.params
    hoh = hohmann(p["r1_km"], p["r2_km"]).total_m_s
    bi = best_bielliptic(p["r1_km"], p["r2_km"], p["ra_max_km"]).total_m_s
    if p["winner"] == "bielliptic":
        assert hoh - bi >= FAMILY.template["min_strategy_gap_m_s"]
        assert hoh > p["budget_m_s"] + 5.0 - 1e-9          # Hohmann is out of the budget with room to spare
    else:
        assert p["r2_km"] / p["r1_km"] <= FAMILY.template["max_hohmann_ratio"]
        assert bi == pytest.approx(hoh, abs=1e-9)           # the best bi-elliptic is Hohmann itself


def test_both_strategies_appear_among_the_instances():
    assert {instance(s).params["winner"] for s in range(10)} == {"hohmann", "bielliptic"}


@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_plan_spends_the_optimum_and_ends_by_the_final_epoch(seed):
    inst = instance(seed)
    ref = FAMILY.reference(inst)
    p = inst.params
    assert len(ref.maneuvers) == (2 if p["winner"] == "hohmann" else 3)
    total = 1000.0 * sum(abs(m.delta_v_km_s[0]) for m in ref.maneuvers)
    assert total == pytest.approx(FAMILY.reference_delta_v_m_s(inst), rel=1e-12)
    assert total <= p["budget_m_s"]
    last = parse_epoch(ref.maneuvers[-1].epoch_utc)
    assert parse_epoch(inst.final_epoch) - last == FAMILY.template["final_margin_s"] * 1000 or p["winner"] == "bielliptic"


@pytest.mark.parametrize("seed", SEEDS)
def test_draws_respect_the_template(seed):
    rg = FAMILY.template["ranges"]
    p = instance(seed).params
    assert rg["r1_km"][0] <= p["r1_km"] <= rg["r1_km"][1] and rg["r2_km"][0] <= p["r2_km"] <= rg["r2_km"][1]
    assert p["ra_max_km"] >= 1.29 * p["r2_km"]


def test_instances_are_deterministic_and_seeds_differ():
    assert instance(7) == instance(7)
    assert instance(7).params != instance(9).params


def test_only_the_maneuvers_mode_exists():
    with pytest.raises(ValueError):
        generate("hohmann_or_bielliptic_plan", 0, "values")


def test_statement_gives_the_radii_the_deadline_and_the_budget():
    inst = instance(5)
    p = inst.params
    for fragment in (str(p["r1_km"]), str(p["r2_km"]), "398600.4415", inst.epoch, inst.final_epoch,
                     f"{p['budget_m_s']} m/s", "finished", "VNB", "<final_answer>"):
        assert fragment in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]
    assert str(p["ra_max_km"]) not in inst.statement   # the bound is carried by the deadline, not announced
