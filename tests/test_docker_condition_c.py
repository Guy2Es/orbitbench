# tests/test_docker_condition_c.py
"""Condition C in Docker: the Python service plus the gmat-mcp server, with a scripted model."""
import json
import time

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
    "import importlib.util as u, os, socket, json\n"
    "found = {m: bool(u.find_spec(m)) for m in ('numpy', 'scipy', 'sgp4', 'core', 'gmatpy', 'mcp')}\n"
    "try:\n    socket.gethostbyname('gmat'); gmat_host = True\nexcept OSError:\n    gmat_host = False\n"
    "print(json.dumps({'modules': found, 'gmat_host': gmat_host, 'opt_gmat': os.path.exists('/opt/gmat'),\n"
    "                  'opt_app': os.path.exists('/opt/app')}))\n"
)


def call(tool, **args):
    return ModelOutput.for_tool_call(MODEL, tool, args)


def reply(inst):
    return ModelOutput.from_content(MODEL, "Done.\n" + render_reply(FAMILIES[inst.family].reference(inst)))


def run(insts, outputs, tmp_path):
    task = build_task(insts, "C")
    log = inspect_eval(task, model=get_model(MODEL, custom_outputs=outputs), display="none", log_dir=str(tmp_path),
                       max_samples=1)[0]
    assert log.status == "success", log.error
    return log.samples


def tool_texts(sample):
    return [(m.function, m.text, m.error) for m in sample.messages if m.role == "tool"]


def test_python_does_not_reach_gmat_and_the_gmat_tools_work(tmp_path):
    inst = next(i for i in instances() if i.mode == "values")
    start = time.perf_counter()
    [sample] = run([inst], [
        call("python", code=PROBE),
        call("suggest_hohmann_transfer", from_sma_km=6778.137, to_sma_km=42164.0),
        call("create_spacecraft", name="Sat", sma_km=6778.137, ecc=0.0, inc_deg=28.5),
        call("get_spacecraft_state", name="Sat"),
        reply(inst)], tmp_path)
    print(f"condition C episode: {time.perf_counter() - start:.1f} s")
    texts = tool_texts(sample)
    probe = json.loads(texts[0][1])
    assert probe["modules"] == {"numpy": True, "scipy": True, "sgp4": True, "core": False, "gmatpy": False,
                                "mcp": False}
    assert not probe["gmat_host"] and not probe["opt_gmat"] and not probe["opt_app"]
    assert [t[0] for t in texts] == ["python", "suggest_hohmann_transfer", "create_spacecraft", "get_spacecraft_state"]
    assert all(t[2] is None for t in texts), texts
    assert "Sat" in texts[3][1]
    assert sample.scores["orbitbench_scorer"].value["solved"] == 1.0


def test_a_new_episode_does_not_see_the_previous_session(tmp_path):
    a, b = [i for i in instances() if i.mode == "values"][:2]
    first, second = run([a, b], [
        call("create_spacecraft", name="Leftover", sma_km=7000.0, ecc=0.0, inc_deg=10.0), reply(a),
        call("get_spacecraft_state", name="Leftover"), reply(b)], tmp_path)
    assert tool_texts(first)[0][2] is None
    _, _, error = tool_texts(second)[0]
    assert error is not None and "No spacecraft named 'Leftover'" in error.message
