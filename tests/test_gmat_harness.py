# tests/test_gmat_harness.py
"""The whole harness against GMAT, with a scripted model that answers with the reference: no Docker."""
import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai.model import ModelOutput, get_model

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES
from orbitbench.harness.catalog import instances
from orbitbench.harness.task import build_task

pytestmark = pytest.mark.gmat
MODEL = "mockllm/model"


def run(insts, replies, tmp_path):
    """Samples run one at a time, in order, so each scripted reply meets its own instance."""
    outputs = [ModelOutput.from_content(MODEL, r) for r in replies]
    log = inspect_eval(build_task(insts, tools=[], sandbox=None), model=get_model(MODEL, custom_outputs=outputs),
                       display="none", log_dir=str(tmp_path), max_samples=1)[0]
    assert log.status == "success", log.error
    return log.samples


def test_the_reference_solves_the_61_instances(tmp_path):
    insts = instances()
    samples = run(insts, [render_reply(FAMILIES[i.family].reference(i)) for i in insts], tmp_path)
    assert len(samples) == 61
    scores = {s.id: s.scores["orbitbench_scorer"] for s in samples}
    failed = {k: v.metadata["outcome"] for k, v in scores.items() if v.metadata["outcome"] != "solved"}
    assert not failed, failed
    assert all(v.value["reward"] == pytest.approx(1.0, abs=1e-6) for v in scores.values())


def test_a_wrong_plan_gets_its_label(tmp_path):
    inst = next(i for i in instances() if i.family == "frame_trap")
    ref = FAMILIES["frame_trap"].reference(inst)
    wrong = ref.model_copy(update={"maneuvers": [ref.maneuvers[0].model_copy(
        update={"frame": "LVLH", "delta_v_km_s": [ref.maneuvers[0].delta_v_km_s[1], 0.0, 0.0]})]})
    sample = run([inst], [render_reply(wrong)], tmp_path)[0]
    score = sample.scores["orbitbench_scorer"]
    assert score.metadata["outcome"] == "constraints_violated"
    assert score.value["solved"] == 0.0
