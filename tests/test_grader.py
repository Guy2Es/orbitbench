# tests/test_grader.py
"""The grader's labels and reward, with a canned replay so no GMAT is needed."""
import pytest

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import REWARD_SCALE_M_S, Outcome, grade, reward
from orbitbench.replay import Replay, plan_delta_v_m_s

VALUES = generate("hohmann", 6, "values")
PLAN = generate("hohmann", 6, "maneuvers")
REF_VALUES = FAMILIES["hohmann"].reference(VALUES)
REF_PLAN = FAMILIES["hohmann"].reference(PLAN)


def final_state(**patch) -> dict:
    return {"sma_km": PLAN.params["r2_km"], "ecc": 1e-5, "inc_deg": PLAN.params["inc_deg"], **patch}


def canned(status="ok", reason=None, final=None, answer_dv=None):
    """A replay_fn that returns a fixed result instead of running GMAT."""
    def replay_fn(instance, answer, job_dir):
        dv = plan_delta_v_m_s(answer) if answer_dv is None else answer_dv
        return Replay(status == "ok", status, reason, final if final is not None else final_state(), dv)
    return replay_fn


def plan_grade(answer=REF_PLAN, **kw):
    return grade(PLAN, render_reply(answer), replay_fn=canned(**kw))


# --- values mode ---------------------------------------------------------------------------------

def test_values_reference_is_solved():
    assert grade(VALUES, render_reply(REF_VALUES)).outcome is Outcome.SOLVED


def test_values_within_tolerance_is_solved_and_beyond_it_is_not():
    ref = REF_VALUES.values["delta_v_total_m_s"]
    for offset, outcome in ((0.9, Outcome.SOLVED), (-0.9, Outcome.SOLVED), (1.1, Outcome.VALUES_MISMATCH)):
        answer = REF_VALUES.model_copy(update={"values": {"delta_v_total_m_s": ref + offset}})
        assert grade(VALUES, render_reply(answer)).outcome is outcome


def test_values_in_km_s_instead_of_m_s_is_a_mismatch():
    answer = REF_VALUES.model_copy(update={"values": {"delta_v_total_m_s": REF_VALUES.values["delta_v_total_m_s"] / 1000}})
    assert grade(VALUES, render_reply(answer)).outcome is Outcome.VALUES_MISMATCH


def test_values_answer_without_the_field_is_a_format_failure():
    answer = REF_VALUES.model_copy(update={"values": {"other": 1.0}})
    assert grade(VALUES, render_reply(answer)).outcome is Outcome.INVALID_FORMAT


# --- any mode ------------------------------------------------------------------------------------

def test_a_reply_without_a_block_is_a_format_failure():
    result = grade(VALUES, "It is about 3900 m/s.")
    assert result.outcome is Outcome.INVALID_FORMAT and result.reward == 0.0


def test_ill_posed_on_a_well_posed_instance_is_a_wrong_status():
    answer = REF_VALUES.model_copy(update={"status": "ill_posed", "reason": "not enough data"})
    assert grade(VALUES, render_reply(answer)).outcome is Outcome.WRONG_STATUS


# --- maneuvers mode ------------------------------------------------------------------------------

def test_a_plan_that_meets_every_constraint_is_solved_with_full_reward():
    result = plan_grade()
    assert result.outcome is Outcome.SOLVED and result.reward == pytest.approx(1.0, abs=1e-6)
    assert all(c["met"] for c in result.detail["checks"])


@pytest.mark.parametrize("patch, quantity", [
    ({"sma_km": PLAN.params["r2_km"] * 1.01}, "sma_km"), ({"ecc": 0.01}, "ecc"),
    ({"inc_deg": PLAN.params["inc_deg"] + 0.01}, "inc_deg")])
def test_each_violated_constraint_is_reported(patch, quantity):
    result = plan_grade(final=final_state(**patch))
    assert result.outcome is Outcome.CONSTRAINTS_VIOLATED
    assert [c["quantity"] for c in result.detail["checks"] if not c["met"]] == [quantity]
    assert 0.0 < result.reward < 1.0


def test_declared_delta_v_that_contradicts_the_plan_is_a_mismatch():
    answer = REF_PLAN.model_copy(update={"values": {"delta_v_total_m_s": 1000.0}})
    assert plan_grade(answer).outcome is Outcome.VALUES_MISMATCH


def test_no_declared_delta_v_is_fine_for_a_plan():
    answer = REF_PLAN.model_copy(update={"values": {}})
    assert plan_grade(answer).outcome is Outcome.SOLVED


@pytest.mark.parametrize("status, outcome", [
    ("invalid_plan", Outcome.INVALID_PLAN), ("failed", Outcome.RUN_FAILED), ("timeout", Outcome.RUN_FAILED),
    ("crashed", Outcome.RUN_FAILED), ("epoch_mismatch", Outcome.REPLAY_ERROR)])
def test_replay_failures_get_their_own_label_and_no_reward(status, outcome):
    result = plan_grade(status=status, reason="why", final={})
    assert result.outcome is outcome and result.reward == 0.0 and not result.passed


# --- reward --------------------------------------------------------------------------------------

def test_reward_is_one_at_the_optimum_and_never_above():
    assert reward(1.0, 0.0) == 1.0 and reward(1.0, -5.0) == 1.0


def test_reward_decreases_with_the_gap_and_with_unmet_constraints():
    gaps = [0.0, 1.0, 10.0, 100.0, 1e4]
    values = [reward(1.0, g) for g in gaps]
    assert values == sorted(values, reverse=True) and all(0.0 < v <= 1.0 for v in values)
    assert reward(2 / 3, 0.0) < reward(1.0, 0.0) and reward(0.0, 0.0) == 0.0


def test_reward_halves_at_the_scale():
    assert reward(1.0, REWARD_SCALE_M_S) == pytest.approx(0.5)


def test_a_plan_above_the_optimum_earns_less_than_the_reference():
    answer = REF_PLAN.model_copy(update={"values": {}})
    heavy = Replay(True, "ok", None, final_state(), plan_delta_v_m_s(answer) + 50.0)
    result = grade(PLAN, render_reply(answer), replay_fn=lambda *a: heavy)
    assert result.outcome is Outcome.SOLVED and result.reward < 0.2
