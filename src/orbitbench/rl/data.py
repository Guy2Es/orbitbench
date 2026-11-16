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
    """`n` training instances following the mix, deterministic and distinct. Instance i takes slot i % 18 of the schedule;
    its seed is first_seed + 3 * cycle + occurrence, where `occurrence` counts the earlier slots of the same family in the
    cycle (0 to 2). So the 18 instances of a cycle are all different, and a trap keeps the seed of its twin (same numbers,
    well posed). Sample ids (family:mode:seed) are unique, which Inspect needs."""
    if first_seed < TRAIN_FIRST_SEED:
        raise ValueError(f"training seeds start at {TRAIN_FIRST_SEED}: lower seeds are development or test seeds")
    size = len(TRAIN_SCHEDULE)
    out = []
    for i in range(n):
        cycle, slot = divmod(i, size)
        family, mode = TRAIN_SCHEDULE[slot]
        base = family.removesuffix("_twin")
        occurrence = sum(f.removesuffix("_twin") == base for f, _ in TRAIN_SCHEDULE[:slot] if f.endswith("_twin") == family.endswith("_twin"))
        out.append(generate(family, first_seed + 3 * cycle + occurrence, mode))
    return out


def harness_system_message(condition: str = "A") -> str:
    """The system message the harness really sends: the text of prompt.py, then the paragraph that Inspect's react agent
    adds to it (its default assistant prompt; the harness does not switch it off). Same for every model."""
    from inspect_ai.agent._types import DEFAULT_ASSISTANT_PROMPT
    return system_prompt(condition) + "\n\n" + DEFAULT_ASSISTANT_PROMPT


def chat_of(instance: Instance, condition: str = "A") -> list[dict]:
    """The exact messages a model sees in the benchmark: the system message of the harness, then the statement."""
    return [{"role": "system", "content": harness_system_message(condition)}, {"role": "user", "content": instance.statement}]


# Blocks of 144 distinct instances (8 cycles of 18, 24 seeds each) never overlap: each (training seed, round, redraw) owns a
# range of BLOCK_STRIDE seeds. 3 training seeds x 2 rounds x 2 redraws use seeds below 1,012,000; phase 0 starts at 1,900,000.
BLOCK_STRIDE = 1000
PHASE0_FIRST_SEED = 1_900_000


def block_first_seed(train_seed: int, round_: int, redraw: int = 0) -> int:
    """First seed of the block that training seed `train_seed` plays in round `round_` (0 or 1); `redraw` is 1 for the
    second block of round 0, played only if the first kept fewer than 48 rewarded replies (docs/rl_plan.md)."""
    if not (0 <= train_seed < 3 and round_ in (0, 1) and redraw in (0, 1)):
        raise ValueError("train_seed in 0..2, round in 0..1, redraw in 0..1")
    return TRAIN_FIRST_SEED + BLOCK_STRIDE * (4 * train_seed + 2 * round_ + redraw)
