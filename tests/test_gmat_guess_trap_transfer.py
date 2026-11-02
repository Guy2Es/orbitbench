# tests/test_gmat_guess_trap_transfer.py
"""The guess trap in GMAT: a Target from the suggested value diverges while the job still reports ok."""
import pytest

from orbitbench import gmat_mcp
from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.reference.hohmann import hohmann

pytestmark = pytest.mark.gmat
NAME = "guess_trap_transfer"


def instance_and_reference(seed):
    inst = generate(NAME, seed, "maneuvers")
    return inst, FAMILIES[NAME].reference(inst)


def target_from(inst, guess_km_s, tmp_path):
    """Runs a GMAT Target that varies the first burn from `guess_km_s` until the apoapsis radius is r2."""
    assert gmat_mcp.add_to_path()
    from core.runner import run_mission
    from core.spec import load_mission
    spec = {"spec_version": "1", "name": "guess", "central_body": "Earth", "epoch": inst.epoch,
            "spacecraft": [{"name": inst.satellite, "state": inst.initial_state}],
            "force_models": [{"name": "FM"}], "propagators": [{"name": "Prop", "force_model": "FM"}],
            "sequence": [{"type": "target", "name": "DC", "body": [
                {"type": "impulsive_burn", "name": "B", "spacecraft": inst.satellite, "delta_v_km_s": [0, 0, 0]}],
                "vary": [{"burn": "B", "initial_km_s": guess_km_s}],
                "achieve": [{"spacecraft": inst.satellite, "quantity": "apoapsis_radius_km",
                             "value": inst.params["r2_km"]}]}]}
    return run_mission(load_mission(spec), tmp_path / "job", timeout_s=120)


@pytest.mark.parametrize("seed", range(6))
def test_the_reference_plan_passes_the_grader(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    result = grade(inst, render_reply(ref), tmp_path / "job")
    assert result.outcome is Outcome.SOLVED, result.detail
    assert result.reward == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("seed", range(8))
def test_a_target_from_the_suggested_value_does_not_converge_yet_the_job_is_ok(seed, tmp_path):
    inst, _ = instance_and_reference(seed)
    run = target_from(inst, inst.params["guess_km_s"], tmp_path)
    assert run.run.ok
    assert run.results.targets[0].converged is False


@pytest.mark.parametrize("seed", range(4))
def test_a_target_from_the_true_burn_converges_on_it(seed, tmp_path):
    inst, _ = instance_and_reference(seed)
    first = hohmann(inst.params["r1_km"], inst.params["r2_km"]).delta_v1_km_s
    run = target_from(inst, first, tmp_path)
    assert run.results.targets[0].converged is True
    assert run.results.targets[0].controls["B.1"] == pytest.approx(first, rel=1e-6)


def test_the_suggested_value_used_as_the_burn_fails_the_grader(tmp_path):
    inst, ref = instance_and_reference(1)
    first = ref.maneuvers[0].model_copy(update={"delta_v_km_s": [inst.params["guess_km_s"], 0.0, 0.0]})
    result = grade(inst, render_reply(ref.model_copy(update={"maneuvers": [first, ref.maneuvers[1]]})), tmp_path / "job")
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert not result.passed


def test_burns_in_m_s_instead_of_km_s_fail(tmp_path):
    inst, ref = instance_and_reference(4)
    scaled = [m.model_copy(update={"delta_v_km_s": [c * 1000.0 for c in m.delta_v_km_s]}) for m in ref.maneuvers]
    result = grade(inst, render_reply(ref.model_copy(update={"maneuvers": scaled})), tmp_path / "job")
    assert not result.passed
