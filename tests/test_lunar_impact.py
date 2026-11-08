# tests/test_lunar_impact.py
"""lunar_impact: generator from the built table, statement, grading of the impact date, and the reference against GMAT."""
import pytest

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES, generate
from orbitbench.families.lunar_draw import MOON_RADIUS_KM, candidates
from orbitbench.families.lunar_impact import load_table
from orbitbench.families.base import load_template
from orbitbench.grader import Outcome, grade

pytestmark_table = pytest.mark.skipif(not load_table(), reason="lunar_impact_table.yaml has not been built")
SEEDS = sorted(load_table())[:5]


def test_candidates_are_reproducible_and_inside_the_ranges():
    tpl = load_template("lunar_impact")
    a = [p for _, p in zip(range(5), candidates(3, tpl["ranges"], tpl["epoch_start"], tpl["epoch_days"]))]
    b = [p for _, p in zip(range(5), candidates(3, tpl["ranges"], tpl["epoch_start"], tpl["epoch_days"]))]
    assert a == b
    rg = tpl["ranges"]
    for p in a:
        alt = p["sma_km"] * (1 - p["ecc"]) - MOON_RADIUS_KM
        assert rg["periapsis_alt_km"][0] - 0.1 <= alt <= rg["periapsis_alt_km"][1] + 0.1
        assert rg["inc_deg"][0] <= p["inc_deg"] <= rg["inc_deg"][1]


@pytestmark_table
@pytest.mark.parametrize("seed", SEEDS)
def test_instance_has_an_answer_inside_the_horizon(seed):
    inst = generate("lunar_impact", seed, "values")
    assert inst.level == 4 and inst.gravity["file"] == "GRGM900C" and inst.gravity["degree"] == 50
    assert 0 < inst.params["impact_days"] <= load_template("lunar_impact")["max_days"]
    assert "GRGM900C" in inst.statement and "DE405" in inst.statement and "MOON_PA" in inst.statement and "values.impact_days" in inst.statement
    assert inst.epoch in inst.statement and "<final_answer>" in inst.statement


@pytestmark_table
def test_statement_does_not_leak_the_answer():
    inst = generate("lunar_impact", SEEDS[0], "values")
    assert f"{inst.params['impact_days']:.2f}" not in inst.statement


@pytestmark_table
def test_grading_accepts_the_reference_and_rejects_a_wrong_date():
    inst = generate("lunar_impact", SEEDS[0], "values")
    ref = FAMILIES["lunar_impact"].reference(inst)
    assert grade(inst, render_reply(ref)).passed
    exact = inst.params["impact_days"]
    near = ref.model_copy(update={"values": {"impact_days": exact + 0.9}})
    far = ref.model_copy(update={"values": {"impact_days": exact + 1.5}})
    assert grade(inst, render_reply(near)).passed
    result = grade(inst, render_reply(far))
    assert not result.passed and result.outcome == Outcome.VALUES_MISMATCH


@pytestmark_table
def test_unbuilt_seed_is_a_clear_error():
    with pytest.raises(KeyError, match="build_lunar_table"):
        generate("lunar_impact", 10**6, "values")


@pytestmark_table
def test_the_table_is_deterministic_in_its_seed():
    """The row of a seed starts from the first candidate of its stream, plus `rejected` skipped ones."""
    tpl = load_template("lunar_impact")
    for seed in SEEDS:
        row = load_table()[seed]
        stream = candidates(seed, tpl["ranges"], tpl["epoch_start"], tpl["epoch_days"])
        for _ in range(row["rejected"]):
            next(stream)
        assert next(stream) == row["params"]
