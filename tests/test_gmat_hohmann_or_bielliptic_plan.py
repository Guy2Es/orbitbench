# tests/test_gmat_hohmann_or_bielliptic_plan.py
"""The Hohmann-or-bielliptic family replayed in GMAT: the reference plan must pass, the wrong strategy must not."""
import pytest

from orbitbench.answer import Maneuver, render_reply
from orbitbench.epoch import add_seconds
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.reference.bielliptic import bielliptic
from orbitbench.reference.hohmann import hohmann

pytestmark = pytest.mark.gmat
NAME = "hohmann_or_bielliptic_plan"


def instance_and_reference(seed):
    inst = generate(NAME, seed, "maneuvers")
    return inst, FAMILIES[NAME].reference(inst)


def of_winner(winner):
    return next(s for s in range(20) if generate(NAME, s, "maneuvers").params["winner"] == winner)


def graded(inst, answer, tmp_path):
    return grade(inst, render_reply(answer), tmp_path / "job")


def plan(ref, inst, burns):
    return ref.model_copy(update={"maneuvers": [
        Maneuver(epoch_utc=add_seconds(inst.epoch, when), spacecraft=inst.satellite, frame="VNB",
                 delta_v_km_s=[dv, 0.0, 0.0]) for when, dv in burns]})


def failed_checks(result):
    return {c["quantity"] for c in result.detail["checks"] if not c["met"]}


@pytest.mark.parametrize("seed", range(6))
def test_the_reference_plan_passes_the_grader(seed, tmp_path):
    inst, ref = instance_and_reference(seed)
    result = graded(inst, ref, tmp_path)
    assert result.outcome is Outcome.SOLVED, result.detail
    assert result.reward == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("which", range(2))
def test_hohmann_where_bielliptic_wins_busts_the_budget_and_nothing_else(which, tmp_path):
    seed = [s for s in range(20) if generate(NAME, s, "maneuvers").params["winner"] == "bielliptic"][which]
    inst, ref = instance_and_reference(seed)
    p = inst.params
    t = hohmann(p["r1_km"], p["r2_km"])
    result = graded(inst, plan(ref, inst, [(0.0, t.delta_v1_km_s), (t.transfer_time_s, t.delta_v2_km_s)]), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert failed_checks(result) == {"plan_delta_v_m_s"}


def test_a_bielliptic_where_hohmann_wins_cannot_meet_the_deadline(tmp_path):
    # Its second burn falls after the final epoch, which the grader refuses before any replay.
    inst, ref = instance_and_reference(of_winner("hohmann"))
    p = inst.params
    b = bielliptic(p["r1_km"], p["r2_km"], 3.0 * p["r2_km"])
    burns = [(0.0, b.delta_v1_km_s), (b.time_to_second_burn_s, b.delta_v2_km_s), (b.time_to_third_burn_s, b.delta_v3_km_s)]
    result = graded(inst, plan(ref, inst, burns), tmp_path)
    assert result.outcome is Outcome.INVALID_PLAN
    assert "after the final epoch" in result.detail["reason"]


def test_a_missing_last_burn_leaves_the_orbit_eccentric(tmp_path):
    inst, ref = instance_and_reference(of_winner("bielliptic"))
    result = graded(inst, ref.model_copy(update={"maneuvers": ref.maneuvers[:2]}), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert "ecc" in failed_checks(result)


def test_a_third_burn_with_the_wrong_sign_fails(tmp_path):
    inst, ref = instance_and_reference(of_winner("bielliptic"))
    last = ref.maneuvers[-1].model_copy(update={"delta_v_km_s": [-ref.maneuvers[-1].delta_v_km_s[0], 0.0, 0.0]})
    result = graded(inst, ref.model_copy(update={"maneuvers": ref.maneuvers[:2] + [last]}), tmp_path)
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert failed_checks(result) - {"plan_delta_v_m_s"}


def test_burns_in_m_s_instead_of_km_s_fail(tmp_path):
    inst, ref = instance_and_reference(of_winner("hohmann"))
    scaled = [m.model_copy(update={"delta_v_km_s": [c * 1000.0 for c in m.delta_v_km_s]}) for m in ref.maneuvers]
    assert not graded(inst, ref.model_copy(update={"maneuvers": scaled}), tmp_path).passed
