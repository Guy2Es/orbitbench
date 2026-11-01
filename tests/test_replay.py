# tests/test_replay.py
"""Building the Mission Spec that flies a plan: ordering rules and the commands emitted."""
import pytest

from orbitbench.answer import Maneuver
from orbitbench.epoch import add_seconds, parse_epoch
from orbitbench.families import FAMILIES, generate
from orbitbench.replay import MAX_MANEUVERS, PlanError, build_mission, plan_delta_v_m_s

INST = generate("hohmann", 4, "maneuvers")
REF = FAMILIES["hohmann"].reference(INST)


def with_burns(*burns: Maneuver):
    return REF.model_copy(update={"maneuvers": list(burns)})


def burn(epoch: str, dv=(0.1, 0.0, 0.0), **patch) -> Maneuver:
    return Maneuver(epoch_utc=epoch, spacecraft="Sat", frame="VNB", delta_v_km_s=list(dv), **patch)


def types(mission: dict) -> list:
    return [c["type"] for c in mission["sequence"]]


def refused(answer, match):
    with pytest.raises(PlanError, match=match):
        build_mission(INST, answer)


def test_reference_plan_is_burn_then_coast_then_burn_then_coast():
    # The first burn is at the initial epoch: no propagate before it.
    assert types(build_mission(INST, REF)) == ["impulsive_burn", "propagate", "impulsive_burn", "propagate"]


def test_the_last_propagate_stops_on_the_instance_final_epoch():
    last = build_mission(INST, REF)["sequence"][-1]
    assert last["stop"] == {"type": "epoch", "epoch": INST.final_epoch}


def test_burns_are_named_in_order_and_use_the_given_frame():
    burns = [c for c in build_mission(INST, REF)["sequence"] if c["type"] == "impulsive_burn"]
    assert [b["name"] for b in burns] == ["M1", "M2"] and {b["frame"] for b in burns} == {"VNB"}


def test_two_burns_at_the_same_epoch_have_no_propagate_between_them():
    later = add_seconds(INST.epoch, 600)
    mission = build_mission(INST, with_burns(burn(later), burn(later)))
    assert types(mission) == ["propagate", "impulsive_burn", "impulsive_burn", "propagate"]


def test_a_burn_on_the_final_epoch_needs_no_closing_propagate():
    assert types(build_mission(INST, with_burns(burn(INST.final_epoch)))) == ["propagate", "impulsive_burn"]


def test_no_propagate_goes_to_a_date_that_is_not_strictly_later():
    # GMAT runs such a propagate to its 30-day bound and still reports ok.
    five_s = add_seconds(INST.epoch, 5)
    plans = [REF, with_burns(burn(INST.epoch), burn(INST.epoch)), with_burns(burn(five_s), burn(five_s))]
    for answer in plans:
        current = parse_epoch(INST.epoch)
        for command in build_mission(INST, answer)["sequence"]:
            if command["type"] == "propagate":
                stop = parse_epoch(command["stop"]["epoch"])
                assert stop > current
                current = stop


def test_the_initial_state_and_model_come_from_the_instance():
    mission = build_mission(INST, REF)
    assert mission["epoch"] == INST.epoch and mission["spacecraft"][0]["state"] == INST.initial_state
    assert mission["force_models"] == [{"name": "FM"}]   # a point mass: no gravity field, no third body
    assert mission["propagators"][0]["integrator"] == "PrinceDormand78"


def test_a_maneuver_before_the_initial_epoch_is_refused():
    refused(with_burns(burn("31 Dec 2025 23:59:59.000")), "before the initial epoch")


def test_a_maneuver_before_the_previous_one_is_refused():
    refused(with_burns(burn(add_seconds(INST.epoch, 600)), burn(add_seconds(INST.epoch, 599.999))),
            "maneuver 2 is dated before the previous one")


def test_a_maneuver_after_the_final_epoch_is_refused():
    refused(with_burns(burn(add_seconds(INST.final_epoch, 0.001))), "after the final epoch")


def test_another_spacecraft_is_refused():
    refused(with_burns(Maneuver(epoch_utc=INST.epoch, spacecraft="Other", frame="VNB", delta_v_km_s=[0, 0, 0])),
            "spacecraft")


def test_an_impossible_date_is_refused():
    refused(with_burns(burn("31 Feb 2026 00:00:00.000")), "not a UTCGregorian epoch")


def test_too_many_maneuvers_are_refused():
    refused(with_burns(*[burn(INST.epoch)] * (MAX_MANEUVERS + 1)), "more than")


def test_plan_delta_v_is_the_sum_of_burn_norms_in_m_s():
    answer = with_burns(burn(INST.epoch, (0.003, 0.004, 0.0)), burn(INST.epoch, (0.0, 0.0, 0.002)))
    assert plan_delta_v_m_s(answer) == pytest.approx(7.0)


@pytest.mark.parametrize("seed", range(5))
def test_the_mission_passes_gmat_mcp_validation(seed):
    pytest.importorskip("core")
    from core.spec import load_mission
    inst = generate("hohmann", seed, "maneuvers")
    mission = load_mission(build_mission(inst, FAMILIES["hohmann"].reference(inst)))
    assert [c.type for c in mission.sequence] == ["impulsive_burn", "propagate", "impulsive_burn", "propagate"]
