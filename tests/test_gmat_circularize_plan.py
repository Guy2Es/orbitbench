# tests/test_gmat_circularize_plan.py
"""The circularization family replayed in GMAT: the reference burn must pass, wrong plans must fail."""
import dataclasses
import math

import pytest

from orbitbench.answer import render_reply
from orbitbench.epoch import add_seconds
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.reference.circularize import circularize
from orbitbench.reference.kepler import mean_motion

pytestmark = pytest.mark.gmat


def instance_and_reference(seed):
    inst = generate("circularize_plan", seed, "maneuvers")
    return inst, FAMILIES["circularize_plan"].reference(inst)


def graded(inst, answer, tmp_path):
    return grade(inst, render_reply(answer), tmp_path / "job")


def with_burn(ref, **update):
    return ref.model_copy(update={"maneuvers": [ref.maneuvers[0].model_copy(update=update)]})


def failed_checks(result):
    return {c["quantity"] for c in result.detail["checks"] if not c["met"]}


@pytest.mark.parametrize("seed", range(5))
def test_the_reference_burn_passes_the_grader(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    result = graded(inst, ref, tmp_path)
    assert result.outcome is Outcome.SOLVED, result.detail
    assert result.reward == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("seed", range(3))
def test_burning_at_periapsis_makes_a_circle_but_busts_the_budget(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    p = inst.params
    c = circularize(p["sma_km"], p["ecc"], p["ta_deg"])
    t_peri = c.time_to_apoapsis_s + math.pi / mean_motion(p["sma_km"])   # periapsis follows apoapsis
    later = dataclasses.replace(inst, final_epoch=add_seconds(inst.epoch, t_peri + 600.0))
    burn = ref.maneuvers[0].model_copy(update={"epoch_utc": add_seconds(inst.epoch, t_peri),
                                               "delta_v_km_s": [-c.periapsis_dv_km_s, 0.0, 0.0]})
    result = graded(later, ref.model_copy(update={"maneuvers": [burn]}), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert failed_checks(result) == {"plan_delta_v_m_s"}


def test_the_same_burn_at_the_start_leaves_the_orbit_eccentric(tmp_path):
    inst, ref = instance_and_reference(1)
    result = graded(inst, with_burn(ref, epoch_utc=inst.epoch), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert "ecc" in failed_checks(result)


def test_a_burn_a_few_seconds_early_still_circularizes(tmp_path):
    # Documents the timing tolerance: the 0.001 eccentricity bound allows a few seconds.
    inst, ref = instance_and_reference(1)
    shifted = add_seconds(ref.maneuvers[0].epoch_utc, -3.0)
    assert graded(inst, with_burn(ref, epoch_utc=shifted), tmp_path).outcome is Outcome.SOLVED


def test_a_burn_a_minute_early_does_not(tmp_path):
    inst, ref = instance_and_reference(1)
    shifted = add_seconds(ref.maneuvers[0].epoch_utc, -60.0)
    result = graded(inst, with_burn(ref, epoch_utc=shifted), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED and "ecc" in failed_checks(result)


def test_a_retrograde_burn_at_apoapsis_fails(tmp_path):
    inst, ref = instance_and_reference(2)
    v = ref.maneuvers[0].delta_v_km_s
    result = graded(inst, with_burn(ref, delta_v_km_s=[-v[0], 0.0, 0.0]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED and "ecc" in failed_checks(result)


def test_a_burn_in_the_normal_direction_changes_the_plane(tmp_path):
    inst, ref = instance_and_reference(3)
    v = ref.maneuvers[0].delta_v_km_s[0]
    result = graded(inst, with_burn(ref, delta_v_km_s=[0.0, v, 0.0]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED and "inc_deg" in failed_checks(result)


def test_delta_v_in_m_s_instead_of_km_s_fails(tmp_path):
    inst, ref = instance_and_reference(4)
    scaled = [c * 1000.0 for c in ref.maneuvers[0].delta_v_km_s]
    assert not graded(inst, with_burn(ref, delta_v_km_s=scaled), tmp_path).passed
