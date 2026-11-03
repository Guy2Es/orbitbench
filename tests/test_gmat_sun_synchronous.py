# tests/test_gmat_sun_synchronous.py
"""The sun_synchronous references flown in GMAT: the node drift GMAT measures is the Sun's."""
import pytest

from orbitbench.answer import FinalAnswer
from orbitbench.constants import SUN_RATE_DEG_DAY
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.answer import render_reply
from orbitbench.replay import replay

pytestmark = pytest.mark.gmat


def flown(inst, inc, tmp_path):
    answer = FinalAnswer(schema_version="1.0", status="solved", initial_orbit={"inc_deg": inc})
    return replay(inst, answer, tmp_path / "job")


@pytest.mark.parametrize("seed", range(5))
def test_gmat_measures_the_suns_rate_on_the_reference(seed, tmp_path):
    inst = generate("sun_synchronous", seed, "orbit")
    played = flown(inst, FAMILIES["sun_synchronous"].reference_inclination(inst), tmp_path)
    assert played.ok, played.reason
    assert abs(played.final["raan_drift_deg_day"] - SUN_RATE_DEG_DAY) < inst.constraints[0]["abs_tol"] / 4


@pytest.mark.parametrize("seed", range(5))
def test_the_closed_form_answer_is_not_enough(seed, tmp_path):
    inst = generate("sun_synchronous", seed, "orbit")
    reply = render_reply(FinalAnswer(schema_version="1.0", status="solved",
                                     initial_orbit={"inc_deg": FAMILIES["sun_synchronous"].reference_formula(inst)}))
    assert grade(inst, reply, job_dir=tmp_path / "job").outcome is Outcome.CONSTRAINTS_VIOLATED


def test_a_polar_orbit_is_not_sun_synchronous(tmp_path):
    inst = generate("sun_synchronous", 0, "orbit")
    reply = render_reply(FinalAnswer(schema_version="1.0", status="solved", initial_orbit={"inc_deg": 90.0}))
    assert grade(inst, reply, job_dir=tmp_path / "job").outcome is Outcome.CONSTRAINTS_VIOLATED
