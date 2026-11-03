# tests/test_harness_export.py
"""The JSONL export and the command line, with a scripted model: no Docker, no GMAT."""
import json
from pathlib import Path

import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai.model import ModelOutput, get_model

from orbitbench.answer import render_reply
from orbitbench.families import FAMILIES
from orbitbench.harness.catalog import instances
from orbitbench.harness.cli import parse
from orbitbench.harness.export import rows_of, write_jsonl
from orbitbench.harness.report import failures, load, render, tokens
from orbitbench.harness.task import build_task

MODEL = "mockllm/model"


def logs_for(insts, replies, tmp_path, **kw):
    outputs = [ModelOutput.from_content(MODEL, r) for r in replies]
    return inspect_eval(build_task(insts, tools=[], sandbox=None, **kw), model=get_model(MODEL, custom_outputs=outputs),
                        display="none", log_dir=str(tmp_path), max_samples=1)


def test_a_row_carries_the_instance_the_label_and_the_cost(tmp_path):
    insts = [i for i in instances() if i.mode == "values"][:2]
    good = render_reply(FAMILIES[insts[0].family].reference(insts[0]))
    [log] = logs_for(insts, [good, "no block"], tmp_path)
    rows = rows_of(log, "B")
    assert [(r["family"], r["mode"], r["seed"]) for r in rows] == [(i.family, i.mode, i.seed) for i in insts]
    assert [r["outcome"] for r in rows] == ["solved", "invalid_format"]
    assert [r["solved"] for r in rows] == [1.0, 0.0]
    assert all(r["condition"] == "B" and r["model"] == MODEL and r["assistant_turns"] == 1 for r in rows)


def test_a_row_says_what_the_run_was_played_with(tmp_path):
    inst = next(i for i in instances() if i.mode == "values")
    [log] = logs_for([inst], ["a"], tmp_path, message_limit=7, token_limit=123456)
    [row] = rows_of(log, "B")
    assert row["temperature"] == "provider_default" and row["batch"] is False
    assert (row["message_limit"], row["token_limit"], row["epochs"]) == (7, 123456, 1)
    assert row["inspect_ai"] and row["max_tokens"] is None


def test_a_reply_cut_by_the_message_limit_is_labelled_limit(tmp_path):
    inst = next(i for i in instances() if i.mode == "values")
    # tools=[] so the model can only talk; a limit of 1 message ends the episode before the model answers
    [log] = logs_for([inst], ["thinking..."], tmp_path, message_limit=1)
    [row] = rows_of(log, "B")
    assert row["outcome"].startswith("limit_") and row["solved"] == 0.0


def test_write_jsonl_makes_one_line_per_episode(tmp_path):
    insts = [i for i in instances() if i.mode == "values"][:3]
    logs = logs_for(insts, ["a", "b", "c"], tmp_path / "logs")
    path = tmp_path / "episodes.jsonl"
    assert write_jsonl(logs, "C", path) == 3
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 3 and {r["condition"] for r in rows} == {"C"}


def test_per_line_caps_the_seeds_of_every_line():
    capped = instances(per_line=2)
    assert len(capped) == 2 * 11
    assert len(instances(per_line=100)) == len(instances()) == 61
    assert [i.seed for i in instances(per_line=2, first_seed=7) if i.family == "j2_drift"] == [7, 8]


def test_the_report_counts_the_outcomes_the_tokens_and_lists_the_failures(tmp_path):
    insts = [i for i in instances() if i.mode == "values"][:2]
    good = render_reply(FAMILIES[insts[0].family].reference(insts[0]))
    logs = logs_for(insts, [good, "no block"], tmp_path / "logs")
    write_jsonl(logs, "B", tmp_path / "episodes.jsonl")
    rows = load([tmp_path])
    text = render(rows)
    assert "2 episodes, 1 not solved" in text and "invalid_format:1" in text and "solved:1" in text
    assert [r["outcome"] for r in failures(rows)] == ["invalid_format"]
    assert f"{MODEL}" in tokens(rows)


def test_a_token_limit_reaches_the_task():
    inst = next(iter(instances()))
    assert build_task([inst], tools=[], sandbox=None, token_limit=1234).token_limit == 1234
    assert build_task([inst], tools=[], sandbox=None).token_limit is None


def test_the_command_line_parses_a_run():
    args = parse(["run", "--condition", "C", "--model", "mockllm/model", "--log-dir", "runs/x",
                  "--families", "hohmann", "--first-seed", "100", "--max-samples", "2", "--limit", "5",
                  "--per-line", "2", "--token-limit", "50000"])
    assert (args.condition, args.families, args.first_seed, args.max_samples, args.limit) == ("C", ["hohmann"], 100, 2, 5)
    assert (args.per_line, args.token_limit, args.batch) == (2, 50000, False)
    assert parse(["run", "--condition", "B", "--model", "m", "--log-dir", "x", "--batch"]).batch
    assert parse(["report", "runs/a", "runs/b"]).dirs == [Path("runs/a"), Path("runs/b")]
    with pytest.raises(SystemExit):
        parse(["run", "--condition", "D", "--model", "m", "--log-dir", "x"])
