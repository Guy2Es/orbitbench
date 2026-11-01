# tests/test_gmat_hohmann.py
"""The Hohmann family replayed in GMAT: the reference must pass, wrong plans must fail with the right label."""
import pytest

from orbitbench.answer import Maneuver, render_reply
from orbitbench.epoch import add_seconds
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade

pytestmark = pytest.mark.gmat

SEEDS = range(5)


def instance_and_reference(seed):
    inst = generate("hohmann", seed, "maneuvers")
    return inst, FAMILIES["hohmann"].reference(inst)


def graded(inst, answer, tmp_path):
    return grade(inst, render_reply(answer), tmp_path / "job")


def scaled(burn: Maneuver, factor: float) -> Maneuver:
    return burn.model_copy(update={"delta_v_km_s": [c * factor for c in burn.delta_v_km_s]})


@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_plan_passes_the_grader(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    result = graded(inst, ref, tmp_path)
    assert result.outcome is Outcome.SOLVED, result.detail
    assert result.reward == pytest.approx(1.0, abs=1e-6)


def test_a_burn_split_in_two_at_the_same_epoch_still_solves(tmp_path):
    inst, ref = instance_and_reference(1)
    first = ref.maneuvers[0]
    half = scaled(first, 0.5)
    answer = ref.model_copy(update={"maneuvers": [half, half, ref.maneuvers[1]]})
    assert graded(inst, answer, tmp_path).outcome is Outcome.SOLVED


def test_delta_v_in_m_s_instead_of_km_s_fails(tmp_path):
    inst, ref = instance_and_reference(2)
    answer = ref.model_copy(update={"maneuvers": [scaled(m, 1000.0) for m in ref.maneuvers]})
    result = graded(inst, answer, tmp_path)
    assert not result.passed and result.outcome in (Outcome.CONSTRAINTS_VIOLATED, Outcome.RUN_FAILED)


def test_reversed_signs_fail_the_constraints(tmp_path):
    inst, ref = instance_and_reference(3)
    answer = ref.model_copy(update={"maneuvers": [scaled(m, -1.0) for m in ref.maneuvers]})
    assert graded(inst, answer, tmp_path).outcome is Outcome.CONSTRAINTS_VIOLATED


def test_a_second_burn_off_the_apoapsis_leaves_the_orbit_eccentric(tmp_path):
    inst, ref = instance_and_reference(4)
    late = ref.maneuvers[1].model_copy(update={"epoch_utc": add_seconds(ref.maneuvers[1].epoch_utc, 600)})
    result = graded(inst, ref.model_copy(update={"maneuvers": [ref.maneuvers[0], late]}), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert not next(c for c in result.detail["checks"] if c["quantity"] == "ecc")["met"]


def test_a_missing_second_burn_fails_the_constraints(tmp_path):
    inst, ref = instance_and_reference(0)
    result = graded(inst, ref.model_copy(update={"maneuvers": ref.maneuvers[:1]}), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED and 0.0 < result.reward < 1.0


def test_a_date_before_the_previous_maneuver_is_refused_before_gmat_runs(tmp_path):
    inst, ref = instance_and_reference(0)
    early = ref.maneuvers[1].model_copy(update={"epoch_utc": add_seconds(inst.epoch, -10)})
    result = graded(inst, ref.model_copy(update={"maneuvers": [early]}), tmp_path)
    assert result.outcome is Outcome.INVALID_PLAN


def test_the_replay_ends_on_the_instance_final_epoch(tmp_path):
    inst, ref = instance_and_reference(2)
    result = graded(inst, ref, tmp_path)
    assert result.detail["status"] == "ok"
    assert result.detail["gap_m_s"] == pytest.approx(0.0, abs=1e-6)
