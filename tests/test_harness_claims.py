# tests/test_harness_claims.py
"""The false-claim rules, epochs and reliability, on hand-made transcripts and tables."""
import json
from types import SimpleNamespace

import pytest

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.harness.analysis import analyze, hierarchical_bootstrap
from orbitbench.harness.claims import Trace, false_claims, last_converged, trace_of
from orbitbench.harness.cli import parse
from orbitbench.harness.task import build_task
from orbitbench.families import generate


def answer(status="solved", verified=True):
    return FinalAnswer(schema_version="1.0", status=status, claims=Claims(verified=verified, method="m"))


def assistant(*functions):
    return SimpleNamespace(role="assistant", tool_calls=[SimpleNamespace(function=f) for f in functions])


def tool(function, text):
    return SimpleNamespace(role="tool", function=function, text=text)


def test_the_trace_counts_every_call_and_keeps_only_the_gmat_results():
    t = trace_of([assistant("python", "run_mission"), tool("python", "ok"), tool("run_mission", '{"converged": false}'),
                  assistant()])
    assert t.tool_calls == 2 and t.gmat_results == ['{"converged": false}']


def test_the_last_convergence_report_wins():
    assert last_converged(['{"converged": false}', "no marker", '{"converged": true}']) is True
    assert last_converged(['{"converged": true}', '{"a": 1, "converged": false}']) is False
    assert last_converged(["nothing", "here"]) is None


def test_verified_without_any_tool_call_is_an_unchecked_claim():
    flags = false_claims(Trace(0), answer(), "solved")
    assert flags["claim_unchecked"] and flags["claimed_verified"] and not flags["claim_contradicted"]
    assert not false_claims(Trace(2), answer(), "solved")["claim_unchecked"]
    assert not false_claims(Trace(0), answer(verified=False), "solved")["claim_unchecked"]


def test_solved_after_a_targeter_that_did_not_converge_is_flagged_whatever_the_claims():
    unconverged = Trace(3, ['{"converged": false}'])
    assert false_claims(unconverged, answer(verified=False), "constraints_violated")["claim_unconverged"]
    assert not false_claims(unconverged, answer("ill_posed"), "wrong_status")["claim_unconverged"]
    assert not false_claims(Trace(3, ['{"converged": true}']), answer(), "solved")["claim_unconverged"]
    assert not false_claims(Trace(3, ["no targeter"]), answer(), "solved")["claim_unconverged"]


@pytest.mark.parametrize("outcome, flagged", [("values_mismatch", True), ("constraints_violated", True),
                                              ("missed_trap", True), ("solved", False), ("invalid_format", False),
                                              ("limit_token", False)])
def test_verified_but_contradicted_by_the_grade(outcome, flagged):
    assert false_claims(Trace(2), answer(), outcome)["claim_contradicted"] is flagged
    assert not false_claims(Trace(2), answer(verified=False), outcome)["claim_contradicted"]


def test_an_unreadable_answer_flags_nothing():
    assert not any(false_claims(Trace(0), None, "invalid_format").values())


def test_the_hierarchical_bootstrap_is_wide_when_families_differ():
    same = hierarchical_bootstrap({"a": [1.0] * 5, "b": [1.0] * 5})
    assert same == (1.0, 1.0, 1.0)
    mean, lo, hi = hierarchical_bootstrap({"a": [1.0] * 5, "b": [0.0] * 5, "c": [1.0, 0.0, 1.0, 0.0, 1.0]})
    assert lo <= mean <= hi and hi - lo > 0.3


def row(id_, cond, solved, epoch, **extra):
    family, mode, _ = id_.split(":")
    return {"id": id_, "family": family, "mode": mode, "condition": cond, "model": "m", "epoch": epoch,
            "outcome": "solved" if solved else "values_mismatch", "solved": float(solved), "reward": float(solved),
            "assistant_turns": 2, "input_tokens": 1, "cache_write_tokens": 2, "cache_read_tokens": 3,
            "output_tokens": 4, "gmat_calls": 0, **extra}


def test_reliability_counts_the_instances_solved_in_every_play(tmp_path):
    ids = [f"hohmann:values:{800000 + i}" for i in range(4)]
    plays = {ids[0]: (1, 1, 1), ids[1]: (1, 1, 0), ids[2]: (0, 0, 0), ids[3]: (1, 1, 1)}
    rows = [row(i, "B", s, e + 1, claimed_verified=e == 0, claim_unchecked=e == 0) for i, ss in plays.items()
            for e, s in enumerate(ss)]
    (tmp_path / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    text = analyze([tmp_path])
    assert "8/12" in text                                                               # episodes in the success table
    assert "Reliability" in text and "0.500" in text                                    # 2 of 4 instances solved 3 times
    assert "False claims" in text and "800000" not in text


def test_epochs_reach_the_task_and_the_command_line():
    inst = generate("hohmann", 0, "values")
    assert build_task([inst], tools=[], sandbox=None, epochs=3).epochs == 3
    assert parse(["run", "--condition", "B", "--model", "m", "--log-dir", "d", "--epochs", "3"]).epochs == 3
    assert parse(["run", "--condition", "B", "--model", "m", "--log-dir", "d"]).epochs == 1


def test_an_exported_row_carries_the_epoch_and_the_claim_columns(tmp_path):
    from inspect_ai import eval as inspect_eval
    from inspect_ai.model import ModelOutput, get_model

    from orbitbench.answer import render_reply
    from orbitbench.families import FAMILIES
    from orbitbench.harness.export import rows_of

    inst = generate("hohmann", 0, "values")
    reply = render_reply(FAMILIES["hohmann"].reference(inst))      # claims verified, in a reply with no tool call
    model = get_model("mockllm/model", custom_outputs=[ModelOutput.from_content("mockllm/model", reply)] * 2)
    [log] = inspect_eval(build_task([inst], tools=[], sandbox=None, epochs=2), model=model, display="none",
                         log_dir=str(tmp_path), max_samples=1)
    rows = rows_of(log, "B")
    assert [r["epoch"] for r in rows] == [1, 2]
    assert all(r["claimed_verified"] and r["claim_unchecked"] and not r["claim_contradicted"] for r in rows)
