# src/orbitbench/harness/scorer.py
"""The Inspect scorer: grades the final reply with the orbitbench grader, on the host. It never reads tool calls."""
import anyio
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState

from orbitbench.families.base import Instance
from orbitbench.grader import grade
from orbitbench.replay import replay


@scorer(metrics={"solved": [mean(), stderr()], "reward": [mean(), stderr()]})
def orbitbench_scorer(replay_fn=replay):
    async def score(state: TaskState, target: Target) -> Score:
        instance = Instance.from_dict(state.metadata)
        # GMAT blocks: keep it off the event loop so other samples keep running.
        result = await anyio.to_thread.run_sync(lambda: grade(instance, state.output.completion, replay_fn=replay_fn))
        return Score(value={"solved": float(result.passed), "reward": result.reward},
                     answer=state.output.completion[-300:],
                     explanation=f"{result.outcome.value}",
                     metadata={"outcome": result.outcome.value, "detail": result.detail})

    return score
