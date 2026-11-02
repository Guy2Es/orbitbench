# src/orbitbench/harness/task.py
"""The Inspect task: instances in, a react agent with the tools of the condition, the orbitbench scorer."""
from pathlib import Path
from typing import Optional, Sequence

from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.tool import mcp_server_sandbox, python

from orbitbench.families.base import Instance
from orbitbench.harness.prompt import system_prompt
from orbitbench.harness.scorer import orbitbench_scorer

# Declared limits, the same for every model and condition.
MESSAGE_LIMIT = 60
PYTHON_TIMEOUT_S = 60
GMAT_WAIT_S = 45            # how long a gmat-mcp call waits for its job before answering "still going"
GMAT_RUN_TIMEOUT_S = 300    # a GMAT job is killed after this
GMAT_CALL_TIMEOUT_S = 180   # the client gives up on a call after this: above GMAT_WAIT_S
DOCKER_DIR = Path(__file__).resolve().parents[3] / "docker"


def sample_of(instance: Instance) -> Sample:
    return Sample(id=f"{instance.family}:{instance.mode}:{instance.seed}", input=instance.statement,
                  metadata=instance.to_dict())


def gmat_server():
    """The gmat-mcp server of condition C, started in the gmat service. One session per episode, nothing shared."""
    return mcp_server_sandbox(
        name="gmat", sandbox="gmat", command="/opt/venv/bin/python", args=["/opt/app/server.py"], cwd="/opt/app",
        timeout=GMAT_CALL_TIMEOUT_S,
        env={"GMAT_INSTALL": "/opt/gmat", "LD_LIBRARY_PATH": "/opt/gmat/bin", "PYTHONUNBUFFERED": "1",
             "PYTHONDONTWRITEBYTECODE": "1", "GMCP_SESSION_FILE": "", "GMCP_JOBS_DIR": "/tmp/jobs",
             "GMCP_BACKEND": "local", "GMCP_WAIT_S": str(GMAT_WAIT_S), "GMCP_RUN_TIMEOUT_S": str(GMAT_RUN_TIMEOUT_S)})


def build_task(instances: Sequence[Instance], condition: str = "B", *, tools: Optional[list] = None,
               sandbox="docker", replay_fn=None, message_limit: int = MESSAGE_LIMIT,
               token_limit: Optional[int] = None) -> Task:
    """One task for `condition`. `tools`, `sandbox` (None for none) and `replay_fn` are for tests.
    `token_limit` caps the tokens of one episode (a spending guard, not part of the declared limits)."""
    if condition not in ("B", "C"):
        raise ValueError(f"unknown condition {condition!r}")
    if tools is None:
        tools = [python(timeout=PYTHON_TIMEOUT_S)] + ([gmat_server()] if condition == "C" else [])
    if sandbox == "docker":
        sandbox = ("docker", str(DOCKER_DIR / f"compose.{condition.lower()}.yaml"))
    scorer = orbitbench_scorer(replay_fn) if replay_fn else orbitbench_scorer()
    solver = react(prompt=system_prompt(condition), tools=tools, submit=False, attempts=1)
    return Task(dataset=MemoryDataset([sample_of(i) for i in instances]), solver=solver, scorer=scorer,
                sandbox=sandbox, message_limit=message_limit, token_limit=token_limit, name=f"orbitbench_{condition}")
