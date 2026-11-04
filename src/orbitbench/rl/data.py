# src/orbitbench/rl/data.py
"""Training instances: analytical families (no GMAT), seeds far from the development and test ranges."""
from orbitbench.families import generate
from orbitbench.families.base import Instance
from orbitbench.harness.prompt import system_prompt

# Development seeds are 0 to 9 and the maintainer's test range is kept below this number; training starts above it.
TRAIN_FIRST_SEED = 1_000_000

# One cycle of the mix: 12 well-posed number questions, 3 traps (the right answer is 'ill_posed') and their 3 twins
# (same numbers, well posed). The traps stay a fixed share so that 'always ill_posed' cannot pay.
TRAIN_SCHEDULE = (
    ("hohmann", "values"), ("plane_change_dv", "values"), ("tsiolkovsky", "values"), ("escape_velocity", "values"),
    ("hohmann", "values"), ("plane_change_dv", "values"), ("tsiolkovsky", "values"), ("escape_velocity", "values"),
    ("hohmann", "values"), ("plane_change_dv", "values"), ("tsiolkovsky", "values"), ("escape_velocity", "values"),
    ("trap_radius", "values"), ("trap_isp", "values"), ("trap_period", "values"),
    ("trap_radius_twin", "values"), ("trap_isp_twin", "values"), ("trap_period_twin", "values"),
)


def train_instances(n: int, first_seed: int = TRAIN_FIRST_SEED) -> list[Instance]:
    """`n` training instances following the mix, deterministic: instance i takes slot i % 18 and seed first_seed + i // 18."""
    if first_seed < TRAIN_FIRST_SEED:
        raise ValueError(f"training seeds start at {TRAIN_FIRST_SEED}: lower seeds are development or test seeds")
    cycle = len(TRAIN_SCHEDULE)
    return [generate(TRAIN_SCHEDULE[i % cycle][0], first_seed + i // cycle, TRAIN_SCHEDULE[i % cycle][1])
            for i in range(n)]


def chat_of(instance: Instance, condition: str = "A") -> list[dict]:
    """The exact messages a model sees in the benchmark: the system prompt of the condition, then the statement."""
    return [{"role": "system", "content": system_prompt(condition)}, {"role": "user", "content": instance.statement}]
