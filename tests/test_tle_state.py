# tests/test_tle_state.py
"""The tle_state family: synthetic TLE, SGP4 reference, statement, grading."""
import math

import numpy as np
import pytest
from sgp4.api import WGS84, Satrec

from orbitbench.answer import render_reply
from orbitbench.constants import EARTH_MU_KM3_S2
from orbitbench.epoch import parse_epoch
from orbitbench.families import FAMILIES, generate
from orbitbench.families.tle_state import KEYS
from orbitbench.grader import Outcome, grade
from orbitbench.reference.kepler import propagate, solve_kepler
from orbitbench.reference.tle import build_tle, checksum, sgp4_state

FAMILY = FAMILIES["tle_state"]
SEEDS = range(40)


def instance(seed):
    return generate("tle_state", seed, "values")


def test_checksum_matches_a_published_tle():
    # The ISS element set used in the sgp4 documentation.
    line1 = "1 25544U 98067A   19343.69339541  .00001764  00000-0  38792-4 0  9991"
    line2 = "2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472202482"
    assert checksum(line1) == int(line1[68]) and checksum(line2) == int(line2[68])


@pytest.mark.parametrize("seed", SEEDS)
def test_lines_are_69_columns_with_valid_checksums_and_sgp4_reads_them_back(seed):
    p = instance(seed).params
    for line in (p["line1"], p["line2"]):
        assert len(line) == 69 and checksum(line) == int(line[68])
    sat = Satrec.twoline2rv(p["line1"], p["line2"])
    assert math.degrees(sat.inclo) == pytest.approx(p["inc_deg"], abs=1e-4)
    assert math.degrees(sat.nodeo) == pytest.approx(p["raan_deg"], abs=1e-4)
    assert sat.ecco == pytest.approx(p["ecc"], abs=1e-9)
    assert sat.no_kozai * 1440.0 / (2 * math.pi) == pytest.approx(p["mean_motion_rev_day"], abs=1e-7)
    assert sat.bstar == pytest.approx(p["bstar_mantissa"] * 1e-5 * 10.0 ** p["bstar_exponent"], rel=1e-9)


def test_a_known_element_set_round_trips():
    line1, line2 = build_tle(satnum=25544, year=2019, day=343.69339541, bstar_mantissa=38792, bstar_exponent=-4,
                             element_set=999, inc_deg=51.6439, raan_deg=211.2001, ecc=0.0007417, aop_deg=17.6667,
                             mean_anomaly_deg=85.6398, mean_motion_rev_day=15.50103472, rev_number=20248)
    assert line2.startswith("2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472")
    assert Satrec.twoline2rv(line1, line2).satnum == 25544


@pytest.mark.parametrize("seed", SEEDS)
def test_draws_stay_in_the_template_ranges(seed):
    rg, p = FAMILY.template["ranges"], instance(seed).params
    assert rg["mean_motion_rev_day"][0] <= p["mean_motion_rev_day"] <= rg["mean_motion_rev_day"][1]
    assert rg["minutes_after_epoch"][0] <= p["minutes"] <= rg["minutes_after_epoch"][1]
    assert rg["ecc"][0] <= p["ecc"] <= rg["ecc"][1]
    n = p["mean_motion_rev_day"] * 2 * math.pi / 86400.0
    assert (EARTH_MU_KM3_S2 / n ** 2) ** (1 / 3) * (1 - p["ecc"]) >= FAMILY.template["min_periapsis_km"]


def test_instances_are_deterministic_and_seeds_differ():
    assert instance(7) == instance(7)
    assert instance(7).params != instance(8).params


def test_only_the_values_mode_exists():
    with pytest.raises(ValueError):
        generate("tle_state", 0, "maneuvers")


def test_final_epoch_is_the_minutes_after_the_tle_epoch():
    inst = instance(3)
    assert (parse_epoch(inst.final_epoch) - parse_epoch(inst.epoch)) / 60000 == pytest.approx(inst.params["minutes"], abs=1e-3)


def test_statement_gives_the_tle_the_delay_the_model_and_the_frame():
    inst = instance(5)
    p = inst.params
    for fragment in (p["line1"], p["line2"], str(p["minutes"]), "SGP4", "WGS-72", "TEME", "values.vz_km_s",
                     "<final_answer>"):
        assert fragment in inst.statement
    assert f'{p["line1"]}\n{p["line2"]}' in inst.statement
    assert "{" not in inst.statement.split("End your reply")[0]
    for key in KEYS:
        assert f'"{key}"' in inst.statement


@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_is_sgp4_at_the_requested_delay(seed):
    inst = instance(seed)
    p = inst.params
    sat = Satrec.twoline2rv(p["line1"], p["line2"])
    err, pos, vel = sat.sgp4(sat.jdsatepoch, sat.jdsatepochF + p["minutes"] / 1440.0)
    assert err == 0
    ref = FAMILY.reference_values(inst)
    assert [ref[k] for k in KEYS] == pytest.approx([*pos, *vel], abs=1e-9)


def test_the_reference_is_solved_and_a_unit_slip_is_not():
    inst = instance(4)
    ref = FAMILY.reference(inst)
    assert grade(inst, render_reply(ref)).outcome is Outcome.SOLVED
    in_m = ref.model_copy(update={"values": {**ref.values, "x_km": ref.values["x_km"] * 1000.0}})
    assert grade(inst, render_reply(in_m)).outcome is Outcome.VALUES_MISMATCH


def test_one_missing_component_is_a_format_failure():
    inst = instance(4)
    ref = FAMILY.reference(inst)
    partial = {k: v for k, v in ref.values.items() if k != "vz_km_s"}
    assert grade(inst, render_reply(ref.model_copy(update={"values": partial}))).outcome is Outcome.INVALID_FORMAT


@pytest.mark.parametrize("seed", range(10))
def test_a_two_body_orbit_from_the_tle_elements_is_caught(seed):
    # Reading the TLE as osculating elements and propagating a point mass ignores SGP4's drag and J2.
    inst = instance(seed)
    p = inst.params
    sat = Satrec.twoline2rv(p["line1"], p["line2"])
    sma = (EARTH_MU_KM3_S2 / (sat.no_kozai / 60.0) ** 2) ** (1 / 3)
    ecc, m0 = sat.ecco, sat.mo
    ea = solve_kepler(m0, ecc)
    ta = math.degrees(2 * math.atan2(math.sqrt(1 + ecc) * math.sin(ea / 2), math.sqrt(1 - ecc) * math.cos(ea / 2)))
    pos, vel = propagate(sma, ecc, p["inc_deg"], p["raan_deg"], p["aop_deg"], ta, p["minutes"] * 60.0)
    ref = FAMILY.reference(inst)
    wrong = dict(zip(KEYS, [float(c) for c in (*pos, *vel)]))
    assert grade(inst, render_reply(ref.model_copy(update={"values": wrong}))).outcome is Outcome.VALUES_MISMATCH


def test_the_wgs84_constants_stay_inside_the_tolerance():
    # Documents the margin: SGP4 run with the other constant set is a different but accepted answer.
    worst = 0.0
    for seed in SEEDS:
        p = instance(seed).params
        sat = Satrec.twoline2rv(p["line1"], p["line2"], WGS84)
        _, pos, _ = sat.sgp4(sat.jdsatepoch, sat.jdsatepochF + p["minutes"] / 1440.0)
        worst = max(worst, float(np.max(np.abs(np.array(pos) - sgp4_state(p["line1"], p["line2"], p["minutes"])[0]))))
    assert worst < FAMILY.template["tolerance"]["position_km"]
