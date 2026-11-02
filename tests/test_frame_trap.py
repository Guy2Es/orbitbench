# tests/test_frame_trap.py
"""The frame_trap family: a tangential burn written in LVLH."""
import pytest

from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.families import FAMILIES, generate
from orbitbench.families.frame_trap import tangential_dv_km_s
from orbitbench.reference.hohmann import hohmann

FAMILY = FAMILIES["frame_trap"]
SEEDS = range(40)


def instance(seed):
    return generate("frame_trap", seed, "maneuvers")


def test_the_first_burn_of_a_hohmann_transfer_is_the_tangential_burn():
    assert tangential_dv_km_s(7000.0, 42164.0) == pytest.approx(hohmann(7000.0, 42164.0).delta_v1_km_s, rel=1e-12)


def test_lowering_the_other_apsis_is_a_retrograde_burn():
    assert tangential_dv_km_s(20000.0, 12000.0) < 0.0 < tangential_dv_km_s(8000.0, 16000.0)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_burns_along_y_only_and_spends_the_optimum(seed):
    inst = instance(seed)
    ref = FAMILY.reference(inst)
    (burn,) = ref.maneuvers
    assert burn.frame == "LVLH" and burn.delta_v_km_s[0] == 0.0 and burn.delta_v_km_s[2] == 0.0
    assert 1000.0 * abs(burn.delta_v_km_s[1]) == pytest.approx(FAMILY.reference_delta_v_m_s(inst), rel=1e-12)
    assert FAMILY.reference_delta_v_m_s(inst) < inst.params["budget_m_s"]


@pytest.mark.parametrize("seed", SEEDS)
def test_the_orbit_is_circular_and_the_target_keeps_its_other_apsis(seed):
    inst, tpl = instance(seed), FAMILY.template
    p = inst.params
    assert inst.initial_state["ecc"] == 0.0 and p["rp_km"] < p["ra_km"]
    assert (p["rp_km"] == p["r_km"]) if seed % 2 == 0 else (p["ra_km"] == p["r_km"])
    assert p["rp_km"] >= tpl["min_periapsis_km"]
    # a radial burn of the same size misses the targets by far more than the tolerance
    v = (EARTH_MU_KM3_S2 / p["r_km"]) ** 0.5
    e = abs(tangential_dv_km_s(p["r_km"], p["other_apsis_km"])) / v
    assert e * p["r_km"] > 10 * inst.constraints[0]["abs_tol"]


def test_both_directions_appear():
    assert {instance(s).params["direction"] for s in range(4)} == {"forward", "retrograde"}


def test_instances_are_deterministic_and_seeds_differ():
    assert instance(7) == instance(7)
    assert instance(7).params != instance(9).params


def test_only_the_maneuvers_mode_exists():
    with pytest.raises(ValueError):
        generate("frame_trap", 0, "values")


def test_statement_defines_the_lvlh_axes_and_the_goal():
    for seed in (0, 1):
        inst = instance(seed)
        p = inst.params
        for fragment in (str(p["r_km"]), str(p["rp_km"]), str(p["ra_km"]), "398600.4415", inst.epoch, inst.final_epoch,
                         "LVLH", "x points away from the centre", "angular momentum", "direction of motion",
                         "x, y, z", "<final_answer>"):
            assert fragment in inst.statement
        assert "{" not in inst.statement.split("End your reply")[0]
    assert "raise the apoapsis" in instance(0).statement and "lower the periapsis" in instance(1).statement
