# tests/test_harness_task.py
"""The Inspect task and scorer, run with a scripted model: no Docker, no GMAT."""
import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai.model import ModelOutput, get_model

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES
from orbitbench.families.base import Instance
from orbitbench.harness.catalog import V01_LINES, instances
from orbitbench.harness.prompt import system_prompt
from orbitbench.harness.task import build_task
from orbitbench.replay import Replay

MODEL = "mockllm/model"


def run(insts, replies, condition="B", replay_fn=None, tmp_path=None):
    outputs = [ModelOutput.from_content(MODEL, r) for r in replies]
    task = build_task(insts, condition, tools=[], sandbox=None, replay_fn=replay_fn)
    log = inspect_eval(task, model=get_model(MODEL, custom_outputs=outputs), display="none",
                       log_dir=str(tmp_path), max_samples=1)[0]
    assert log.status == "success", log.error
    return log


def reference_reply(inst):
    return "Done.\n" + render_reply(FAMILIES[inst.family].reference(inst))


def test_the_catalog_has_the_61_instances_of_the_plan():
    assert len(V01_LINES) == 11
    all_instances = instances()
    assert len(all_instances) == 61
    assert len({(i.family, i.mode, i.seed) for i in all_instances}) == 61


def test_every_instance_round_trips_through_its_dict():
    for inst in instances():
        assert Instance.from_dict(inst.to_dict()) == inst


def test_the_statement_is_the_whole_input():
    inst = instances(first_seed=0)[0]
    task = build_task([inst], tools=[], sandbox=None)
    sample = task.dataset[0]
    assert sample.input == inst.statement
    assert sample.id == f"{inst.family}:{inst.mode}:{inst.seed}"


def test_both_conditions_share_the_prompt_but_for_the_tools():
    b, c = system_prompt("B").split("\n\n"), system_prompt("C").split("\n\n")
    assert b[0] == c[0] and b[1] != c[1]
    with pytest.raises(ValueError):
        build_task([], "D")


def test_values_replies_are_scored_without_gmat(tmp_path):
    insts = [i for i in instances() if i.mode == "values"][:4]
    log = run(insts, [reference_reply(i) for i in insts], tmp_path=tmp_path)
    for sample in log.samples:
        assert sample.scores["orbitbench_scorer"].value == {"solved": 1.0, "reward": 1.0}
        assert sample.scores["orbitbench_scorer"].metadata["outcome"] == "solved"


def test_failures_keep_their_label(tmp_path):
    insts = [i for i in instances() if i.mode == "values"][:3]
    wrong = render_reply(FAMILIES[insts[1].family].reference(insts[1]).model_copy(update={"status": "ill_posed", "reason": "no"}))
    log = run(insts, ["no block at all", wrong, "<final_answer>{oops</final_answer>"], tmp_path=tmp_path)
    labels = [s.scores["orbitbench_scorer"].metadata["outcome"] for s in log.samples]
    assert labels == ["invalid_format", "wrong_status", "invalid_format"]
    assert all(s.scores["orbitbench_scorer"].value["solved"] == 0.0 for s in log.samples)


def test_a_plan_is_replayed_by_the_injected_replay(tmp_path):
    inst = next(i for i in instances() if i.mode == "maneuvers")
    final = {"sma_km": 1.0}
    seen = []

    def fake(instance, answer, job_dir):
        seen.append(instance.family)
        return Replay(ok=False, status="failed", reason="stub", final=None, plan_delta_v_m_s=0.0)

    log = run([inst], [reference_reply(inst)], replay_fn=fake, tmp_path=tmp_path)
    assert seen == [inst.family]
    assert log.samples[0].scores["orbitbench_scorer"].metadata["outcome"] == "run_failed"


def test_the_metrics_average_solved_and_reward(tmp_path):
    insts = [i for i in instances() if i.mode == "values"][:2]
    log = run(insts, [reference_reply(insts[0]), "nothing"], tmp_path=tmp_path)
    means = {s.name: s.metrics["mean"].value for s in log.results.scores}
    assert means == {"solved": pytest.approx(0.5), "reward": pytest.approx(0.5)}


def test_condition_a_has_no_tool_and_no_sandbox():
    task = build_task(instances(first_seed=0)[:1], "A")
    assert task.sandbox is None
    assert "no tools" in system_prompt("A")


def test_condition_a_is_scored_on_the_reply_alone(tmp_path):
    insts = [i for i in instances(max_level=2) if i.mode == "values"][:2]
    log = run(insts, [reference_reply(i) for i in insts], condition="A", tmp_path=tmp_path)
    assert all(s.scores["orbitbench_scorer"].value["solved"] == 1.0 for s in log.samples)


def test_max_level_keeps_the_low_levels_only():
    assert {i.level for i in instances(max_level=2)} <= {1, 2}
    assert len(instances(max_level=2)) < len(instances())


def test_the_v10_catalog_extends_the_v01_one_without_changing_it():
    from orbitbench.harness.catalog import TWIN_LINES, V10_LINES
    assert V10_LINES[:len(V01_LINES)] == V01_LINES
    found, twins = instances(V10_LINES), instances(TWIN_LINES)
    assert (len(found), len(twins)) == (85, 9)
    assert len({(i.family, i.mode, i.seed) for i in found + twins}) == 94
    assert {i.level for i in found} == {1, 2, 3, 4}
    assert all(not i.well_posed for i in found if i.family.startswith("trap_"))
    assert all(i.well_posed for i in twins)
