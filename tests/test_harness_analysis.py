# tests/test_harness_analysis.py
"""The statistics of the write-up, on small hand-made tables."""
import json
from pathlib import Path

import pytest

from orbitbench.harness.analysis import analyze, paired_bootstrap, wilson
from orbitbench.harness.cli import parse


def row(id_, cond, solved, model="m"):
    family, mode, _ = id_.split(":")
    return {"id": id_, "family": family, "mode": mode, "condition": cond, "model": model,
            "outcome": "solved" if solved else "values_mismatch", "solved": float(solved), "reward": float(solved),
            "assistant_turns": 2, "input_tokens": 1, "cache_write_tokens": 2, "cache_read_tokens": 3,
            "output_tokens": 4, "gmat_calls": 0}


def test_wilson_matches_known_values():
    lo, hi = wilson(8, 10)                  # the textbook interval of 8 successes in 10 trials
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)
    lo, hi = wilson(53, 61)                 # worked by hand: centre 0.8471, half-width 0.0850
    assert lo == pytest.approx(0.762, abs=1e-3) and hi == pytest.approx(0.932, abs=1e-3)
    assert wilson(0, 10)[0] == pytest.approx(0.0, abs=1e-12) and wilson(10, 10)[1] == pytest.approx(1.0, abs=1e-12)
    assert wilson(0, 0) == (0.0, 1.0)


def test_the_paired_bootstrap_of_a_constant_difference_has_no_width():
    assert paired_bootstrap([1.0] * 20) == (1.0, 1.0, 1.0)
    mean, lo, hi = paired_bootstrap([1.0, 0.0, 0.0, 0.0, 1.0, 0.0])
    assert lo <= mean <= hi and lo < hi


def test_the_analysis_pairs_instances_by_id_and_never_prints_one(tmp_path):
    ids = [f"hohmann:values:{900000 + i}" for i in range(6)]
    rows = [row(i, "B", n < 4) for n, i in enumerate(ids)] + [row(i, "C", n < 5) for n, i in enumerate(ids)]
    (tmp_path / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    text = analyze([tmp_path])
    assert "4/6" in text and "5/6" in text and "+0.167" in text
    assert "900000" not in text


def test_the_command_line_parses_analyze():
    assert parse(["analyze", "runs/a", "runs/b"]).dirs == [Path("runs/a"), Path("runs/b")]


def test_failures_are_split_into_refusal_wrong_answer_and_no_answer():
    ids = [f"lunar_impact:values:{n}" for n in range(5)]
    outcomes = ["solved", "wrong_status", "values_mismatch", "invalid_format", "limit_message"]
    rows = []
    for i, o in zip(ids, outcomes):
        r = row(i, "B", o == "solved")
        r["outcome"] = o
        r["providers"] = "Crusoe|Near AI" if o == "solved" else "Crusoe"
        rows.append(r)
    text = analyze_rows(rows)
    lines = text.splitlines()
    head = next(n for n, ln in enumerate(lines) if ln.startswith("Why episodes did not succeed"))
    cells = lines[head + 3].split()                               # after the blank line and the column header
    # model, condition, episodes, then solved, refused, wrong answer, no usable answer, plan or run failed, other
    assert cells[:3] == ["m", "B", "5"] and cells[3:] == ["1", "1", "1", "2", "0", "0"]
    assert "m: Crusoe 5, Near AI 1" in text


def analyze_rows(rows):
    from orbitbench.harness.analysis import render
    return render(rows)


def test_excluded_episodes_are_counted_in_no_result_and_the_levels_table_is_built(tmp_path):
    run = tmp_path / "run-x"
    run.mkdir()
    ids = [f"hohmann:values:{900000 + i}" for i in range(6)]
    rows = [row(i, "B", True) for i in ids] + [row(i, "C", n < 3) for n, i in enumerate(ids)]
    (run / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    exclude = tmp_path / "excluded.json"
    exclude.write_text(json.dumps({"run-x": [ids[5]]}), encoding="utf-8")
    text = analyze([run], exclude=exclude, by_level=True)
    assert "5/5" in text and "3/5" in text and "By level" in text and "C minus B by line" in text
    assert "900000" not in text
    assert parse(["analyze", "r", "--exclude", "e.json", "--by-level"]).by_level is True
