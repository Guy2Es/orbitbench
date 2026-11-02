# tests/test_circularize_plan.py
"""The circularize_plan family: apoapsis burn reference, generator, statement."""
import math

import numpy as np
import pytest

from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.epoch import parse_epoch
from orbitbench.families import FAMILIES, generate
from orbitbench.reference.circularize import circularize
from orbitbench.reference.kepler import propagate

FAMILY = FAMILIES["circularize_plan"]
SEEDS = range(40)


def instance(seed):
    return generate("circularize_plan", seed, "maneuvers")


def test_the_apoapsis_burn_is_the_cheapest_single_burn_that_circularizes():
    # A burn at any point can make the orbit circular at that radius: scan them all.
    for ecc in (0.1, 0.3, 0.6):
        a, mu = 10000.0, EARTH_MU_KM3_S2
        p = a * (1 - ecc**2)
        nu = np.linspace(0.0, np.pi, 20001)
        r = p / (1 + ecc * np.cos(nu))
        dv = np.hypot(math.sqrt(mu / p) * ecc * np.sin(nu), np.sqrt(mu / r) - math.sqrt(mu / p) * (1 + ecc * np.cos(nu)))
        assert dv.min() == pytest.approx(circularize(a, ecc, 0.0).apoapsis_dv_km_s, rel=1e-9)
        assert dv.argmin() == len(nu) - 1


@pytest.mark.parametrize("seed", SEEDS)
def test_the_time_to_apoapsis_puts_the_spacecraft_at_apoapsis(seed):
    p = instance(seed).params
    c = circularize(p["sma_km"], p["ecc"], p["ta_deg"])
    pos, vel = propagate(p["sma_km"], p["ecc"], p["inc_deg"], p["raan_deg"], p["aop_deg"], p["ta_deg"],
                         c.time_to_apoapsis_s)
    assert np.linalg.norm(pos) == pytest.approx(p["sma_km"] * (1 + p["ecc"]), rel=1e-9)
    assert pos @ vel == pytest.approx(0.0, abs=1e-6)
    assert 0.0 < c.time_to_apoapsis_s <= 2 * math.pi / math.sqrt(EARTH_MU_KM3_S2 / p["sma_km"] ** 3)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_apoapsis_burn_leaves_a_circular_orbit_of_the_apoapsis_radius(seed):
    p = instance(seed).params
    c = circularize(p["sma_km"], p["ecc"], p["ta_deg"])
    pos, vel = propagate(p["sma_km"], p["ecc"], p["inc_deg"], p["raan_deg"], p["aop_deg"], p["ta_deg"],
                         c.time_to_apoapsis_s)
    vel = vel * (1.0 + c.apoapsis_dv_km_s / np.linalg.norm(vel))
    assert vel @ vel == pytest.approx(EARTH_MU_KM3_S2 / np.linalg.norm(pos), rel=1e-12)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_periapsis_strategy_always_exceeds_the_budget(seed):
    p = instance(seed).params
    c = circularize(p["sma_km"], p["ecc"], p["ta_deg"])
    assert c.best_km_s == c.apoapsis_dv_km_s
    assert 1000.0 * c.periapsis_dv_km_s > p["budget_m_s"] + 1.0   # clear of the 1 m/s margin


@pytest.mark.parametrize("seed", SEEDS)
def test_draws_respect_the_template(seed):
    tpl = FAMILY.template
    p = instance(seed).params
    assert p["sma_km"] * (1 - p["ecc"]) >= tpl["min_periapsis_km"]
    assert abs(p["ta_deg"] - 180.0) >= tpl["min_apsis_distance_deg"]
    assert tpl["ranges"]["ecc"][0] <= p["ecc"] <= tpl["ranges"]["ecc"][1]


def test_instances_are_deterministic_and_seeds_differ():
    assert instance(7) == instance(7)
    assert instance(7).params != instance(8).params


def test_only_the_maneuvers_mode_exists():
    with pytest.raises(ValueError):
        generate("circularize_plan", 0, "values")


def test_final_epoch_is_after_the_reference_burn():
    inst = instance(3)
    burn = FAMILY.reference(inst).maneuvers[0]
    assert parse_epoch(inst.final_epoch) - parse_epoch(burn.epoch_utc) == FAMILY.template["final_margin_s"] * 1000


def test_statement_gives_the_orbit_the_model_and_the_budget():
    inst = instance(5)
    p = inst.params
    for fragment in (str(p["sma_km"]), str(p["ecc"]), str(p["ta_deg"]), "398600.4415", inst.epoch, inst.final_epoch,
                     f"{p['budget_m_s']} m/s", "single impulsive burn", "VNB", "<final_answer>"):
        assert fragment in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]


def test_the_budget_is_the_optimum_plus_the_margin():
    inst = instance(2)
    assert inst.params["budget_m_s"] == pytest.approx(
        FAMILY.reference_delta_v_m_s(inst) + FAMILY.template["dv_margin_m_s"], abs=0.05)
    assert next(c for c in inst.constraints if c["quantity"] == "plan_delta_v_m_s")["max"] == inst.params["budget_m_s"]
