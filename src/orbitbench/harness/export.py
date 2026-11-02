# src/orbitbench/harness/export.py
"""One JSONL row per episode, from an Inspect log: the table the analysis reads. Transcripts stay in the log."""
import json
from pathlib import Path

from inspect_ai.log import EvalLog


def rows_of(log: EvalLog, condition: str) -> list[dict]:
    rows = []
    for sample in log.samples or []:
        family, mode, seed = sample.id.split(":")
        score = sample.scores.get("orbitbench_scorer") if sample.scores else None
        outcome = score.metadata["outcome"] if score else None
        if sample.limit is not None:
            outcome = f"limit_{sample.limit.type}"       # the reply was cut short: the label says why
        elif sample.error is not None:
            outcome = "error"
        usage = list((sample.model_usage or {}).values())
        rows.append({
            "id": sample.id, "family": family, "mode": mode, "seed": int(seed), "condition": condition,
            "model": log.eval.model, "outcome": outcome,
            "solved": score.value["solved"] if score else 0.0, "reward": score.value["reward"] if score else 0.0,
            "assistant_turns": sum(m.role == "assistant" for m in sample.messages),
            "tool_calls": sum(m.role == "tool" for m in sample.messages),
            # input_tokens excludes the cached ones: the whole input is the three columns together
            "input_tokens": sum(u.input_tokens for u in usage),
            "cache_write_tokens": sum(u.input_tokens_cache_write or 0 for u in usage),
            "cache_read_tokens": sum(u.input_tokens_cache_read or 0 for u in usage),
            "output_tokens": sum(u.output_tokens for u in usage),
            "total_time_s": sample.total_time, "working_time_s": sample.working_time,
            "error": sample.error.message[:500] if sample.error else None,
        })
    return rows


def write_jsonl(logs: list[EvalLog], condition: str, path: Path) -> int:
    rows = [row for log in logs for row in rows_of(log, condition)]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return len(rows)
