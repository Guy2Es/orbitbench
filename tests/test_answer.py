# tests/test_answer.py
"""The <final_answer> block: extraction and schema."""
import json

import pytest

from orbitbench.answer import AnswerError, FinalAnswer, extract_answer, render_reply

BASE = {"schema_version": "1.0", "status": "solved", "values": {"delta_v_total_m_s": 3893.2}}
BURN = {"epoch_utc": "01 Jan 2026 00:00:00.000", "spacecraft": "Sat", "frame": "VNB", "delta_v_km_s": [2.4, 0, 0]}


def reply(data) -> str:
    return f"Reasoning...\n<final_answer>{json.dumps(data)}</final_answer>"


def rejected(text: str, label: str):
    with pytest.raises(AnswerError) as info:
        extract_answer(text)
    assert info.value.label == label


def test_values_answer():
    answer = extract_answer(reply(BASE))
    assert answer.status == "solved" and answer.values["delta_v_total_m_s"] == 3893.2


def test_maneuvers_answer():
    answer = extract_answer(reply({**BASE, "maneuvers": [BURN], "claims": {"verified": True, "method": "propagation"}}))
    assert answer.maneuvers[0].frame == "VNB" and answer.claims.verified


def test_the_last_block_wins():
    text = reply({**BASE, "values": {"delta_v_total_m_s": 1.0}}) + "\nCorrection:\n" + reply(BASE)
    assert extract_answer(text).values["delta_v_total_m_s"] == 3893.2


def test_render_and_extract_round_trip():
    answer = FinalAnswer.model_validate({**BASE, "maneuvers": [BURN]})
    assert extract_answer(render_reply(answer)) == answer


def test_no_block():
    rejected("The answer is 3893.", "no_final_answer")


def test_not_json():
    rejected("<final_answer>{'a': 1}</final_answer>", "not_json")
    rejected("<final_answer>```json\n{}\n```</final_answer>", "not_json")


@pytest.mark.parametrize("patch", [
    {"schema_version": "2.0"}, {"status": "maybe"}, {"unknown_field": 1}, {"values": {"x": "high"}},
    {"maneuvers": [{**BURN, "frame": "RTN"}]}, {"maneuvers": [{**BURN, "delta_v_km_s": [1, 2]}]},
    {"maneuvers": [{**BURN, "epoch_utc": "2026-01-01"}]}, {"maneuvers": [{**BURN, "extra": 1}]},
])
def test_schema_violations(patch):
    rejected(reply({**BASE, **patch}), "schema")


def test_nan_is_refused():
    rejected('<final_answer>{"schema_version": "1.0", "status": "solved", "values": {"x": NaN}}</final_answer>',
             "schema")
