# tests/test_canary.py
"""The canaries: trivial, graded without GMAT, and kept out of every suite that is counted."""
import pytest

from orbitbench.answer import FinalAnswer, render_reply
from orbitbench.families import FAMILIES, generate
from orbitbench.grader import Outcome, grade
from orbitbench.harness.catalog import CANARY_LINES, TWIN_LINES, V01_LINES, V10_LINES, instances


@pytest.mark.parametrize("seed", range(3))
def test_the_reference_answer_is_solved(seed):
    inst = generate("canary", seed, "values")
    assert inst.level == 1 and inst.well_posed
    assert grade(inst, render_reply(FAMILIES["canary"].reference(inst))).outcome is Outcome.SOLVED


def test_the_three_instances_ask_three_different_things():
    kinds = {generate("canary", s, "values").params["kind"] for s in range(3)}
    assert kinds == {"circular_speed", "period", "escape_speed"}


def test_a_wrong_value_is_not_solved_and_the_statement_is_deterministic():
    inst = generate("canary", 0, "values")
    key = next(iter(inst.tolerances))
    wrong = FinalAnswer(schema_version="1.0", status="solved", values={key: 1.0})
    assert grade(inst, render_reply(wrong)).outcome is Outcome.VALUES_MISMATCH
    assert generate("canary", 0, "values").statement == inst.statement


def test_the_canaries_are_in_no_counted_suite():
    assert len(instances(CANARY_LINES)) == 3
    for suite in (V01_LINES, V10_LINES, TWIN_LINES):
        assert all(line[0] != "canary" for line in suite)
