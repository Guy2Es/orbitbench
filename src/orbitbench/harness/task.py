# src/orbitbench/harness/task.py
"""The Inspect task: instances in, a react agent with the tools of the condition, the orbitbench scorer."""
from pathlib import Path
from typing import Optional, Sequence

from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.tool import python

from orbitbench.families.base import Instance
from orbitbench.harness.prompt import system_prompt
from orbitbench.harness.scorer import orbitbench_scorer

# Declared limits, the same for every model and condition.
MESSAGE_LIMIT = 60
PYTHON_TIMEOUT_S = 60
DOCKER_DIR = Path(__file__).resolve().parents[3] / "docker"


def sample_of(instance: Instance) -> Sample:
    return Sample(id=f"{instance.family}:{instance.mode}:{instance.seed}", input=instance.statement,
                  metadata=instance.to_dict())


def build_task(instances: Sequence[Instance], condition: str = "B", *, tools: Optional[list] = None,
               sandbox="docker", replay_fn=None, message_limit: int = MESSAGE_LIMIT) -> Task:
    """One task for `condition`. `tools`, `sandbox` (None for none) and `replay_fn` are for tests."""
    if condition not in ("B", "C"):
        raise ValueError(f"unknown condition {condition!r}")
    if tools is None:
        tools = [python(timeout=PYTHON_TIMEOUT_S)]
    if sandbox == "docker":
        sandbox = ("docker", str(DOCKER_DIR / "compose.yaml"))
    scorer = orbitbench_scorer(replay_fn) if replay_fn else orbitbench_scorer()
    solver = react(prompt=system_prompt(condition), tools=tools, submit=False, attempts=1)
    return Task(dataset=MemoryDataset([sample_of(i) for i in instances]), solver=solver, scorer=scorer,
                sandbox=sandbox, message_limit=message_limit, name=f"orbitbench_{condition}")
