# tests/test_gmat_plane_change_budget_plan.py
"""The plane-change-under-budget family replayed in GMAT: the shared plane change passes, the simple plans do not."""
import pytest

from orbitbench.answer import Maneuver, render_reply
from orbitbench.epoch import add_seconds
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.reference.hohmann import hohmann
from orbitbench.reference.plane_change import plane_change
from orbitbench.reference.plane_change_budget import best_split, split_transfer

pytestmark = pytest.mark.gmat
NAME = "plane_change_budget_plan"


def instance_and_reference(seed):
    inst = generate(NAME, seed, "maneuvers")
    return inst, FAMILIES[NAME].reference(inst)


def graded(inst, answer, tmp_path):
    return grade(inst, render_reply(answer), tmp_path / "job")


def plan(ref, inst, burns):
    return ref.model_copy(update={"maneuvers": [
        Maneuver(epoch_utc=add_seconds(inst.epoch, when), spacecraft=inst.satellite, frame="VNB",
                 delta_v_km_s=[v, n, 0.0]) for when, (v, n) in burns]})


def failed_checks(result):
    return {c["quantity"] for c in result.detail["checks"] if not c["met"]}


@pytest.mark.parametrize("seed", range(6))
def test_the_reference_plan_passes_the_grader(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    result = graded(inst, ref, tmp_path)
    assert result.outcome is Outcome.SOLVED, result.detail
    assert result.reward == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("share", (0.0, 1.0))
def test_the_whole_plane_change_at_one_burn_busts_the_budget_and_nothing_else(share, tmp_path):
    inst, ref = instance_and_reference(1)
    p = inst.params
    t = split_transfer(p["r1_km"], p["r2_km"], p["plane_change_deg"], share * p["plane_change_deg"])
    result = graded(inst, plan(ref, inst, [(0.0, t.burn1_km_s), (t.transfer_time_s, t.burn2_km_s)]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert failed_checks(result) == {"plan_delta_v_m_s"}


def test_a_separate_plane_change_busts_the_budget_and_nothing_else(tmp_path):
    inst, ref = instance_and_reference(2)
    p = inst.params
    h = hohmann(p["r1_km"], p["r2_km"])
    rotation = plane_change(p["r2_km"], p["inc_deg"], p["final_inc_deg"])
    result = graded(inst, plan(ref, inst, [(0.0, (h.delta_v1_km_s, 0.0)), (h.transfer_time_s, (h.delta_v2_km_s, 0.0)),
                                           (h.transfer_time_s, (rotation.along_velocity_km_s, -rotation.along_normal_km_s))]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED, result.detail
    assert failed_checks(result) == {"plan_delta_v_m_s"}


def test_a_small_error_in_the_split_still_fits_the_margin(tmp_path):
    inst, ref = instance_and_reference(3)
    p = inst.params
    best = split_transfer(p["r1_km"], p["r2_km"], p["plane_change_deg"], 0.0)
    b = best_split(p["r1_km"], p["r2_km"], p["plane_change_deg"])
    t = split_transfer(p["r1_km"], p["r2_km"], p["plane_change_deg"], b.first_burn_angle_deg + 0.1)
    assert best.total_m_s > t.total_m_s
    result = graded(inst, plan(ref, inst, [(0.0, t.burn1_km_s), (t.transfer_time_s, t.burn2_km_s)]), tmp_path)
    assert result.outcome is Outcome.SOLVED, result.detail


def test_a_second_burn_with_the_wrong_normal_sign_lowers_the_inclination(tmp_path):
    inst, ref = instance_and_reference(0)
    last = ref.maneuvers[1]
    flipped = last.model_copy(update={"delta_v_km_s": [last.delta_v_km_s[0], -last.delta_v_km_s[1], 0.0]})
    result = graded(inst, ref.model_copy(update={"maneuvers": [ref.maneuvers[0], flipped]}), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert "inc_deg" in failed_checks(result)


def test_burns_in_m_s_instead_of_km_s_fail(tmp_path):
    inst, ref = instance_and_reference(4)
    scaled = [m.model_copy(update={"delta_v_km_s": [c * 1000.0 for c in m.delta_v_km_s]}) for m in ref.maneuvers]
    assert not graded(inst, ref.model_copy(update={"maneuvers": scaled}), tmp_path).passed
