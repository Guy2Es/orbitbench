# tests/test_plane_change_budget_plan.py
"""The plane_change_budget_plan family: split plane change reference, fuel budget, statement."""
import math

import numpy as np
import pytest

from orbitbench.families import FAMILIES, generate
from orbitbench.families.plane_change_budget_plan import simple_strategies_m_s
from orbitbench.reference.hohmann import hohmann
from orbitbench.reference.plane_change import plane_change
from orbitbench.reference.plane_change_budget import (best_split, rocket_delta_v_m_s, separate_plane_change_m_s,
                                                      split_transfer)

FAMILY = FAMILIES["plane_change_budget_plan"]
SEEDS = range(40)


def instance(seed):
    return generate("plane_change_budget_plan", seed, "maneuvers")


def test_without_a_plane_change_the_transfer_is_hohmann():
    t = split_transfer(7000.0, 42164.0, 0.0, 0.0)
    assert t.total_m_s == pytest.approx(hohmann(7000.0, 42164.0).total_m_s, rel=1e-12)


def test_a_plane_change_at_one_burn_costs_the_vector_difference():
    r1, r2, di = 7000.0, 42164.0, 28.5
    t = split_transfer(r1, r2, di, 0.0)
    v2 = math.sqrt(398600.4415 / r2)
    vt2 = math.sqrt(398600.4415 * (2 / r2 - 2 / (r1 + r2)))
    law_of_cosines = math.sqrt(v2**2 + vt2**2 - 2 * v2 * vt2 * math.cos(math.radians(di)))
    assert math.hypot(*t.burn2_km_s) == pytest.approx(law_of_cosines, rel=1e-12)


def test_the_split_beats_both_extremes_and_a_fine_scan_finds_no_better():
    r1, r2, di = 6700.0, 42164.0, 28.5
    best = best_split(r1, r2, di)
    scan = min(split_transfer(r1, r2, di, a).total_m_s for a in np.linspace(0.0, di, 20001))
    assert best.total_m_s <= scan + 1e-9
    assert 0.0 < best.first_burn_angle_deg < di
    assert best.total_m_s < split_transfer(r1, r2, di, 0.0).total_m_s < split_transfer(r1, r2, di, di).total_m_s


def test_the_classic_leo_to_geo_split_is_a_couple_of_degrees_at_the_first_burn():
    assert best_split(6700.0, 42164.0, 28.5).first_burn_angle_deg == pytest.approx(2.2, abs=0.1)


def test_separating_the_plane_change_costs_more_than_a_pure_rotation_alone():
    r1, r2, di = 7000.0, 30000.0, 40.0
    assert separate_plane_change_m_s(r1, r2, di) == pytest.approx(
        hohmann(r1, r2).total_m_s + plane_change(r2, 0.0, di).total_m_s, rel=1e-12)


def test_the_rocket_equation_gives_the_published_delta_v():
    # 1000 kg with 500 kg of fuel at Isp 300 s: ve = 2942 m/s, ln 2.
    assert rocket_delta_v_m_s(1000.0, 500.0, 300.0) == pytest.approx(300.0 * 9.80665 * math.log(2.0))


@pytest.mark.parametrize("seed", SEEDS)
def test_the_fuel_allows_the_optimum_with_a_small_margin_and_no_simple_plan(seed):
    inst = instance(seed)
    p, tpl = inst.params, FAMILY.template
    best = best_split(p["r1_km"], p["r2_km"], p["plane_change_deg"]).total_m_s
    assert p["budget_m_s"] == pytest.approx(rocket_delta_v_m_s(p["initial_mass_kg"], p["fuel_mass_kg"], p["isp_s"]), abs=1e-3)
    assert best < p["budget_m_s"] < best + 2.0 * tpl["dv_margin_m_s"]
    for name, cost in simple_strategies_m_s(p["r1_km"], p["r2_km"], p["plane_change_deg"]).items():
        assert cost - p["budget_m_s"] >= tpl["min_strategy_gap_m_s"] - tpl["dv_margin_m_s"], name
    assert p["fuel_mass_kg"] < p["initial_mass_kg"]


@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_plan_spends_the_optimum_at_the_two_nodes(seed):
    inst = instance(seed)
    ref = FAMILY.reference(inst)
    total = 1000.0 * sum(math.hypot(*m.delta_v_km_s) for m in ref.maneuvers)
    assert total == pytest.approx(FAMILY.reference_delta_v_m_s(inst), rel=1e-12)
    assert len(ref.maneuvers) == 2 and total <= inst.params["budget_m_s"]
    assert ref.maneuvers[0].epoch_utc == inst.epoch


@pytest.mark.parametrize("seed", SEEDS)
def test_draws_respect_the_template(seed):
    rg = FAMILY.template["ranges"]
    p = instance(seed).params
    for key in ("r1_km", "r2_km", "inc_deg", "plane_change_deg", "initial_mass_kg", "isp_s"):
        assert rg[key][0] <= p[key] <= rg[key][1], key
    assert p["final_inc_deg"] == pytest.approx(p["inc_deg"] + p["plane_change_deg"], abs=0.051)


def test_instances_are_deterministic_and_seeds_differ():
    assert instance(7) == instance(7)
    assert instance(7).params != instance(9).params


def test_only_the_maneuvers_mode_exists():
    with pytest.raises(ValueError):
        generate("plane_change_budget_plan", 0, "values")


def test_statement_gives_the_fuel_data_not_the_budget():
    inst = instance(5)
    p = inst.params
    for fragment in (str(p["r1_km"]), str(p["r2_km"]), str(p["final_inc_deg"]), "398600.4415", inst.epoch,
                     inst.final_epoch, f"{p['initial_mass_kg']} kg", f"{p['fuel_mass_kg']} kg", f"{p['isp_s']} s",
                     "9.80665", "ascending node", "angular momentum", "<final_answer>"):
        assert fragment in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]
    assert str(p["budget_m_s"]) not in inst.statement
