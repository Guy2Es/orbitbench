# tests/test_gmat_rendezvous_phasing.py
"""The rendezvous_phasing reference flown in GMAT: the grader accepts it, and refuses a plan that is a minute off."""
import pytest

from orbitbench.answer import render_reply
from orbitbench.epoch import add_seconds
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade

pytestmark = pytest.mark.gmat


@pytest.mark.parametrize("seed", range(5))
def test_the_reference_plan_is_solved_in_gmat(seed, tmp_path):
    inst = generate("rendezvous_phasing", seed, "maneuvers")
    result = grade(inst, render_reply(FAMILIES["rendezvous_phasing"].reference(inst)), job_dir=tmp_path / "job")
    assert result.outcome is Outcome.SOLVED, result.detail
    assert result.reward == pytest.approx(1.0)


def test_a_second_burn_a_minute_early_misses(tmp_path):
    inst = generate("rendezvous_phasing", 0, "maneuvers")
    answer = FAMILIES["rendezvous_phasing"].reference(inst)
    answer.maneuvers[1] = answer.maneuvers[1].model_copy(update={"epoch_utc": add_seconds(inst.final_epoch, -60.0)})
    result = grade(inst, render_reply(answer), job_dir=tmp_path / "job")
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
