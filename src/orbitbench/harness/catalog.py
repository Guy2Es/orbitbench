# src/orbitbench/harness/catalog.py
"""The v0.1 instance lines: which (family, mode) pairs and how many instances each."""
from orbitbench.families import generate
from orbitbench.families.base import Instance

# (family, mode, instances); 11 lines, 61 instances. hohmann covers two lines.
V01_LINES = (
    ("hohmann", "values", 5),
    ("plane_change_dv", "values", 5),
    ("j2_drift", "values", 5),
    ("tle_state", "values", 5),
    ("state_at_date", "values", 5),
    ("hohmann", "maneuvers", 6),
    ("hohmann_or_bielliptic_plan", "maneuvers", 6),
    ("plane_change_budget_plan", "maneuvers", 6),
    ("circularize_plan", "maneuvers", 6),
    ("guess_trap_transfer", "maneuvers", 6),
    ("frame_trap", "maneuvers", 6),
)


def instances(lines=V01_LINES, first_seed: int = 0, per_line: int | None = None,
              max_level: int | None = None) -> list[Instance]:
    """Every instance of `lines`, seeds first_seed .. first_seed + n - 1 for each line; `per_line` caps n,
    `max_level` keeps the instances up to that level (condition A: levels 1 and 2)."""
    found = [generate(family, seed, mode) for family, mode, n in lines
             for seed in range(first_seed, first_seed + (n if per_line is None else min(n, per_line)))]
    return [i for i in found if max_level is None or i.level <= max_level]
