# tests/test_guess_trap_transfer.py
"""The guess_trap_transfer family: a Hohmann transfer with a suggested first burn beyond escape."""
import math

import pytest

from orbitbench.families import FAMILIES, generate
from orbitbench.families.guess_trap_transfer import escape_burn_km_s
from orbitbench.reference.hohmann import hohmann

FAMILY = FAMILIES["guess_trap_transfer"]
SEEDS = range(40)


def instance(seed):
    return generate("guess_trap_transfer", seed, "maneuvers")


def test_the_escape_burn_takes_a_circular_orbit_to_parabolic_speed():
    r = 7000.0
    v = math.sqrt(398600.4415 / r)
    assert v + escape_burn_km_s(r) == pytest.approx(math.sqrt(2.0) * v, rel=1e-12)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_suggested_guess_is_beyond_escape_and_far_from_the_true_burn(seed):
    inst = instance(seed)
    p = inst.params
    assert p["guess_km_s"] > 1.05 * escape_burn_km_s(p["r1_km"])
    assert p["guess_km_s"] > 1.3 * hohmann(p["r1_km"], p["r2_km"]).delta_v1_km_s


@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_is_the_hohmann_plan_inside_the_budget(seed):
    inst = instance(seed)
    ref = FAMILY.reference(inst)
    total = 1000.0 * sum(abs(m.delta_v_km_s[0]) for m in ref.maneuvers)
    assert total == pytest.approx(hohmann(inst.params["r1_km"], inst.params["r2_km"]).total_m_s, rel=1e-12)
    assert total < inst.params["budget_m_s"] < total + 2.0


def test_instances_are_deterministic_and_seeds_differ():
    assert instance(7) == instance(7)
    assert instance(7).params != instance(9).params


def test_only_the_maneuvers_mode_exists():
    with pytest.raises(ValueError):
        generate("guess_trap_transfer", 0, "values")


def test_statement_gives_the_guess_as_an_unchecked_note():
    inst = instance(5)
    p = inst.params
    for fragment in (str(p["r1_km"]), str(p["r2_km"]), f"{p['guess_km_s']} km/s", "398600.4415", inst.epoch,
                     inst.final_epoch, f"{p['budget_m_s']} m/s", "have not been checked", "<final_answer>"):
        assert fragment in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]
