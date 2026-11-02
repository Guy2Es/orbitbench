# tests/test_docker_condition_b.py
"""Condition B in Docker: the Python service, isolated, with a scripted model."""
import json

import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai.model import ModelOutput, get_model

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES
from orbitbench.harness.catalog import instances
from orbitbench.harness.task import build_task

pytestmark = pytest.mark.docker
MODEL = "mockllm/model"

PROBE = (
    "import importlib.util as u, socket, json\n"
    "found = {m: bool(u.find_spec(m)) for m in ('numpy', 'scipy', 'sgp4', 'core', 'gmatpy', 'orbitbench')}\n"
    "s = socket.socket(); s.settimeout(3)\n"
    "try:\n    s.connect(('1.1.1.1', 53)); net = True\nexcept OSError:\n    net = False\n"
    "print(json.dumps({'modules': found, 'network': net}))\n"
)


def run(inst, outputs, tmp_path, condition="B"):
    task = build_task([inst], condition)
    log = inspect_eval(task, model=get_model(MODEL, custom_outputs=outputs), display="none", log_dir=str(tmp_path))[0]
    assert log.status == "success", log.error
    return log.samples[0]


def tool_output(sample):
    return next(m.text for m in sample.messages if m.role == "tool")


def test_the_python_service_has_the_libraries_and_nothing_else(tmp_path):
    inst = next(i for i in instances() if i.mode == "values")
    reply = "Done.\n" + render_reply(FAMILIES[inst.family].reference(inst))
    sample = run(inst, [ModelOutput.for_tool_call(MODEL, "python", {"code": PROBE}),
                        ModelOutput.from_content(MODEL, reply)], tmp_path)
    seen = json.loads(tool_output(sample))
    assert seen["modules"] == {"numpy": True, "scipy": True, "sgp4": True, "core": False, "gmatpy": False,
                               "orbitbench": False}
    assert seen["network"] is False
    assert sample.scores["orbitbench_scorer"].value["solved"] == 1.0


def test_a_value_computed_in_the_service_is_graded(tmp_path):
    inst = next(i for i in instances() if i.family == "tle_state")
    ref = FAMILIES["tle_state"].reference(inst)
    code = "from sgp4.api import Satrec\nprint('sgp4 ok', Satrec.__name__)"
    sample = run(inst, [ModelOutput.for_tool_call(MODEL, "python", {"code": code}),
                        ModelOutput.from_content(MODEL, render_reply(ref))], tmp_path)
    assert "sgp4 ok" in tool_output(sample)
    assert sample.scores["orbitbench_scorer"].value["solved"] == 1.0
