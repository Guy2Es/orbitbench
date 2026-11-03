# tests/test_gmat_finite_burn_raise.py
"""The finite-burn references flown in GMAT: the integrated pair of burns circularizes the orbit, the impulsive guesses
do not."""
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
    assert [c["met"] for c in result.detail["checks"]] == [False, False, True]


def test_the_first_burn_alone_leaves_the_periapsis_low(tmp_path):
    inst = generate("finite_burn_raise", 1, "finite")
    first = FAMILIES["finite_burn_raise"].reference(inst).finite_burns[:1]
    result = grade(inst, render_reply(FinalAnswer(schema_version="1.0", status="solved", finite_burns=first)),
                   job_dir=tmp_path / "job")
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert [c["met"] for c in result.detail["checks"]] == [True, False, True]


def test_a_circularization_by_the_impulsive_formula_misses_in_gmat(tmp_path):
    """Both burns sized by Tsiolkovsky, the second one starting at the apoapsis: the plan most models would try."""
    inst = generate("finite_burn_raise", 2, "finite")
    reference = FAMILIES["finite_burn_raise"].reference(inst).finite_burns
    p = inst.params
    naive = FiniteBurn(epoch_utc=reference[1].epoch_utc, spacecraft=inst.satellite,
                       duration_s=impulsive_duration_s(p["r1_km"], p["ra_km"], p["thrust_n"], p["isp_s"], 1450.0),
                       direction="prograde")
    result = grade(inst, render_reply(FinalAnswer(schema_version="1.0", status="solved",
                                                  finite_burns=[reference[0], naive])), job_dir=tmp_path / "job")
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
