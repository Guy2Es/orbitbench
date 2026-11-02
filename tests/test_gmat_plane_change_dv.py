# tests/test_gmat_plane_change_dv.py
"""The plane-change family replayed in GMAT: the reference burn must pass, wrong burns must fail."""
import pytest

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade

pytestmark = pytest.mark.gmat


def instance_and_reference(seed):
    inst = generate("plane_change_dv", seed, "maneuvers")
    return inst, FAMILIES["plane_change_dv"].reference(inst)


def graded(inst, answer, tmp_path):
    return grade(inst, render_reply(answer), tmp_path / "job")


def burn_with(ref, components):
    return ref.model_copy(update={"maneuvers": [ref.maneuvers[0].model_copy(update={"delta_v_km_s": components})]})


@pytest.mark.parametrize("seed", range(5))
def test_the_reference_burn_passes_the_grader(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    result = graded(inst, ref, tmp_path)
    assert result.outcome is Outcome.SOLVED, result.detail
    assert result.reward == pytest.approx(1.0, abs=1e-6)


def test_a_burn_along_the_normal_only_leaves_the_orbit_off_target(tmp_path):
    inst, ref = instance_and_reference(1)
    normal_only = [0.0, ref.maneuvers[0].delta_v_km_s[1], 0.0]
    result = graded(inst, burn_with(ref, normal_only), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert not next(c for c in result.detail["checks"] if c["quantity"] == "sma_km")["met"] or \
        not next(c for c in result.detail["checks"] if c["quantity"] == "ecc")["met"]


def test_the_opposite_normal_burn_moves_the_inclination_the_wrong_way(tmp_path):
    inst, ref = instance_and_reference(2)
    v, n, b = ref.maneuvers[0].delta_v_km_s
    result = graded(inst, burn_with(ref, [v, -n, b]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert not next(c for c in result.detail["checks"] if c["quantity"] == "inc_deg")["met"]


def test_delta_v_in_m_s_instead_of_km_s_fails(tmp_path):
    inst, ref = instance_and_reference(3)
    scaled = [c * 1000.0 for c in ref.maneuvers[0].delta_v_km_s]
    result = graded(inst, burn_with(ref, scaled), tmp_path)
    assert not result.passed


def test_no_burn_at_all_leaves_the_inclination_unchanged(tmp_path):
    inst, ref = instance_and_reference(4)
    result = graded(inst, ref.model_copy(update={"maneuvers": []}), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED and 0.0 < result.reward < 1.0
