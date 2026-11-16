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


# v1.0: the 11 lines of v0.1 (unchanged, so that v0.1 stays reproducible), the three level-4 lines and the ill-posed
# traps. 14 lines + 3 trap lines: 61 + 15 + 9 = 85 instances. The well-posed twins of the traps are reported apart.
LEVEL_FOUR_LINES = (
    ("sun_synchronous", "orbit", 5),
    ("rendezvous_phasing", "maneuvers", 5),
    ("finite_burn_raise", "finite", 5),
)
TRAP_LINES = tuple((f"trap_{kind}", "values", 3) for kind in ("radius", "isp", "period"))
TWIN_LINES = tuple((f"{family}_twin", mode, n) for family, mode, n in TRAP_LINES)
V10_LINES = V01_LINES + LEVEL_FOUR_LINES + TRAP_LINES
# Three trivial questions, played with every run and never counted in its results: a failure means a broken harness.
CANARY_LINES = (("canary", "values", 3),)
# After the v1.0 freeze, under docs/lunar_baseline_rule.md: the lunar impact date, 15 seeds built in the table.
LUNAR_LINES = (("lunar_impact", "values", 15),)
# The same line on the private test seeds (30 consecutive integers, `--first-seed` is the first of them, see freeze.md).
LUNAR_TEST_LINES = (("lunar_impact", "values", 30),)

# The RL study (docs/rl_plan.md, amendment of 12 Nov 2026), played on its own private seed range, condition B.
# In distribution: the four number families, the three traps and their twins, as in training. 24 + 18 + 18 = 60.
RL_IN_LINES = (
    ("hohmann", "values", 6), ("plane_change_dv", "values", 6), ("tsiolkovsky", "values", 6), ("escape_velocity", "values", 6),
    *((f"trap_{kind}", "values", 6) for kind in ("radius", "isp", "period")),
    *((f"trap_{kind}_twin", "values", 6) for kind in ("radius", "isp", "period")),
)
# Near transfer: the same physics asked as level-3 plans, and three other value families. 10 + 10 + 18 = 38.
RL_NEAR_LINES = (
    ("hohmann", "maneuvers", 10), ("plane_change_dv", "maneuvers", 10),
    ("state_at_date", "values", 6), ("j2_drift", "values", 6), ("tle_state", "values", 6),
)
# Held out: two plan families the model never saw (declared on 4 Nov 2026). 40.
RL_HELD_OUT_LINES = (("hohmann_or_bielliptic_plan", "maneuvers", 20), ("plane_change_budget_plan", "maneuvers", 20))
RL_LINES = RL_IN_LINES + RL_NEAR_LINES + RL_HELD_OUT_LINES      # 138 instances


def instances(lines=V01_LINES, first_seed: int = 0, per_line: int | None = None,
              max_level: int | None = None) -> list[Instance]:
    """Every instance of `lines`, seeds first_seed .. first_seed + n - 1 for each line; `per_line` caps n,
    `max_level` keeps the instances up to that level (condition A: levels 1 and 2)."""
    found = [generate(family, seed, mode) for family, mode, n in lines
             for seed in range(first_seed, first_seed + (n if per_line is None else min(n, per_line)))]
    return [i for i in found if max_level is None or i.level <= max_level]
