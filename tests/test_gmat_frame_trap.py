# tests/test_gmat_frame_trap.py
"""The frame trap replayed in GMAT: the same numbers in the wrong slot give a different orbit, silently."""
import pytest

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade

pytestmark = pytest.mark.gmat
NAME = "frame_trap"


def instance_and_reference(seed):
    inst = generate(NAME, seed, "maneuvers")
    return inst, FAMILIES[NAME].reference(inst)


def burn(ref, frame, vector):
    return ref.model_copy(update={"maneuvers": [ref.maneuvers[0].model_copy(
        update={"frame": frame, "delta_v_km_s": list(vector)})]})


def graded(inst, answer, tmp_path):
    return grade(inst, render_reply(answer), tmp_path / "job")


def failed_checks(result):
    return {c["quantity"] for c in result.detail["checks"] if not c["met"]}


@pytest.mark.parametrize("seed", range(6))
def test_the_reference_plan_passes_the_grader(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    result = graded(inst, ref, tmp_path)
    assert result.outcome is Outcome.SOLVED, result.detail
    assert result.reward == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("seed", range(4))
def test_the_velocity_slot_habit_of_vnb_makes_a_radial_burn_in_lvlh(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    dv = ref.maneuvers[0].delta_v_km_s[1]
    result = graded(inst, burn(ref, "LVLH", [dv, 0.0, 0.0]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert {"rp_km", "ra_km"} <= failed_checks(result)


def test_the_burn_along_z_tilts_the_plane(tmp_path):
    inst, ref = instance_and_reference(2)
    dv = ref.maneuvers[0].delta_v_km_s[1]
    result = graded(inst, burn(ref, "LVLH", [0.0, 0.0, dv]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert "inc_deg" in failed_checks(result)


@pytest.mark.parametrize("seed", (0, 1))
def test_a_burn_against_the_motion_fails(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    dv = ref.maneuvers[0].delta_v_km_s[1]
    result = graded(inst, burn(ref, "LVLH", [0.0, -dv, 0.0]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert {"rp_km", "ra_km"} & failed_checks(result)


def test_the_same_manoeuvre_in_vnb_is_right_too(tmp_path):
    # The statement asks for LVLH, but the grader judges the physical result, so VNB [dv, 0, 0] is the same burn.
    inst, ref = instance_and_reference(3)
    dv = ref.maneuvers[0].delta_v_km_s[1]
    assert graded(inst, burn(ref, "VNB", [dv, 0.0, 0.0]), tmp_path).outcome is Outcome.SOLVED


def test_burns_in_m_s_instead_of_km_s_fail(tmp_path):
    inst, ref = instance_and_reference(4)
    scaled = [c * 1000.0 for c in ref.maneuvers[0].delta_v_km_s]
    assert not graded(inst, burn(ref, "LVLH", scaled), tmp_path).passed
