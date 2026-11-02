# tests/test_gmat_finite_burn_raise.py
"""The finite-burn references flown in GMAT: the integrated duration reaches the apoapsis, the impulsive one does not."""
import pytest

from orbitbench.answer import FinalAnswer, FiniteBurn, render_reply
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.reference.finite_burn import impulsive_duration_s

pytestmark = pytest.mark.gmat


@pytest.mark.parametrize("seed", range(5))
def test_the_reference_burn_is_solved_in_gmat(seed, tmp_path):
    inst = generate("finite_burn_raise", seed, "finite")
    result = grade(inst, render_reply(FAMILIES["finite_burn_raise"].reference(inst)), job_dir=tmp_path / "job")
    assert result.outcome is Outcome.SOLVED, result.detail


def test_the_impulsive_duration_falls_short_in_gmat(tmp_path):
    inst = generate("finite_burn_raise", 0, "finite")
    p = inst.params
    guess = impulsive_duration_s(p["r1_km"], p["ra_km"], p["thrust_n"], p["isp_s"], 1450.0)
    burn = FiniteBurn(epoch_utc=inst.epoch, spacecraft=inst.satellite, duration_s=guess)
    answer = FinalAnswer(schema_version="1.0", status="solved", finite_burns=[burn])
    result = grade(inst, render_reply(answer), job_dir=tmp_path / "job")
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert [c["met"] for c in result.detail["checks"]] == [False, True]
