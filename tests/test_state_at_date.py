# tests/test_state_at_date.py
"""The state_at_date family: Kepler reference, instance generator, statement, grading."""
import math

import numpy as np
import pytest

from orbitbench.answer import render_reply
from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.families import FAMILIES, generate
from orbitbench.families.state_at_date import KEYS
from orbitbench.grader import Outcome, grade
from orbitbench.reference.kepler import mean_motion, propagate, solve_kepler, state_from_elements

FAMILY = FAMILIES["state_at_date"]
SEEDS = range(40)


def test_solving_kepler_inverts_the_equation_even_at_high_eccentricity():
    for ecc in (0.0, 0.3, 0.7, 0.95):
        for m in (-3.0, 0.1, 1.0, 3.1, 6.0):
            e = solve_kepler(m, ecc)
            assert math.remainder(e - ecc * math.sin(e) - m, 2 * math.pi) == pytest.approx(0.0, abs=1e-12)


def test_after_one_period_the_state_is_the_initial_one():
    elements = (12000.0, 0.4, 30.0, 40.0, 50.0, 60.0)
    period = 2 * math.pi / mean_motion(12000.0)
    pos0, vel0 = state_from_elements(*elements)
    pos1, vel1 = propagate(*elements, period)
    assert np.allclose(pos0, pos1, atol=1e-6) and np.allclose(vel0, vel1, atol=1e-9)


def test_a_circular_equatorial_orbit_turns_a_quarter_in_a_quarter_period():
    r = 8000.0
    period = 2 * math.pi / mean_motion(r)
    pos, vel = propagate(r, 0.0, 0.0, 0.0, 0.0, 0.0, period / 4)
    assert np.allclose(pos, [0.0, r, 0.0], atol=1e-6)
    assert np.allclose(vel, [-math.sqrt(EARTH_MU_KM3_S2 / r), 0.0, 0.0], atol=1e-9)


@pytest.mark.parametrize("seed", SEEDS)
def test_energy_and_angular_momentum_are_conserved(seed):
    p = generate("state_at_date", seed, "values").params
    elements = (p["sma_km"], p["ecc"], p["inc_deg"], p["raan_deg"], p["aop_deg"], p["ta_deg"])
    pos0, vel0 = state_from_elements(*elements)
    pos1, vel1 = propagate(*elements, p["dt_s"])
    energy = lambda r, v: v @ v / 2 - EARTH_MU_KM3_S2 / np.linalg.norm(r)
    assert energy(pos1, vel1) == pytest.approx(energy(pos0, vel0), rel=1e-11)
    assert np.allclose(np.cross(pos1, vel1), np.cross(pos0, vel0), rtol=1e-9)


def test_instances_are_deterministic_and_seeds_differ():
    assert generate("state_at_date", 7, "values") == generate("state_at_date", 7, "values")
    assert generate("state_at_date", 7, "values").params != generate("state_at_date", 8, "values").params


@pytest.mark.parametrize("seed", SEEDS)
def test_draws_stay_in_the_template_ranges(seed):
    rg = FAMILY.template["ranges"]
    p = generate("state_at_date", seed, "values").params
    for key in ("sma_km", "ecc", "inc_deg", "raan_deg", "aop_deg", "ta_deg"):
        assert rg[key][0] <= p[key] <= rg[key][1]
    assert p["sma_km"] * (1 - p["ecc"]) >= FAMILY.template["min_periapsis_km"]
    assert rg["dt_hours"][0] * 3600 <= p["dt_s"] <= rg["dt_hours"][1] * 3600


def test_only_the_values_mode_exists():
    with pytest.raises(ValueError):
        generate("state_at_date", 0, "maneuvers")


def test_final_epoch_is_the_time_of_flight_after_the_epoch():
    inst = generate("state_at_date", 3, "values")
    from orbitbench.epoch import parse_epoch
    assert (parse_epoch(inst.final_epoch) - parse_epoch(inst.epoch)) / 1000 == inst.params["dt_s"]


def test_statement_fixes_what_the_answer_depends_on():
    inst = generate("state_at_date", 5, "values")
    p = inst.params
    for fragment in (str(p["sma_km"]), str(p["ecc"]), str(p["ta_deg"]), "398600.4415", inst.epoch, inst.final_epoch,
                     "point mass", "mean-equator and mean-equinox of J2000", "values.vx_km_s", "<final_answer>"):
        assert fragment in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]
    for key in KEYS:
        assert f'"{key}"' in inst.statement


def test_the_reference_is_solved_and_a_unit_slip_is_not():
    inst = generate("state_at_date", 4, "values")
    ref = FAMILY.reference(inst)
    assert grade(inst, render_reply(ref)).outcome is Outcome.SOLVED
    in_m = ref.model_copy(update={"values": {**ref.values, "x_km": ref.values["x_km"] * 1000.0}})
    assert grade(inst, render_reply(in_m)).outcome is Outcome.VALUES_MISMATCH


def test_one_missing_component_is_a_format_failure():
    inst = generate("state_at_date", 4, "values")
    ref = FAMILY.reference(inst)
    partial = {k: v for k, v in ref.values.items() if k != "vz_km_s"}
    assert grade(inst, render_reply(ref.model_copy(update={"values": partial}))).outcome is Outcome.INVALID_FORMAT


def test_the_mean_anomaly_mistake_is_caught():
    # Using the true anomaly as if it advanced linearly in time is the classic error: it must fail.
    inst = generate("state_at_date", 6, "values")
    p = inst.params
    ref = FAMILY.reference_values(inst)
    n = math.degrees(mean_motion(p["sma_km"])) * p["dt_s"]
    pos, vel = state_from_elements(p["sma_km"], p["ecc"], p["inc_deg"], p["raan_deg"], p["aop_deg"], p["ta_deg"] + n)
    wrong = dict(zip(ref, [float(c) for c in (*pos, *vel)]))
    ref_answer = FAMILY.reference(inst)
    assert grade(inst, render_reply(ref_answer.model_copy(update={"values": wrong}))).outcome is Outcome.VALUES_MISMATCH
