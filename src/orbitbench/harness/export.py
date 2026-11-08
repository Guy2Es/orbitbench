# src/orbitbench/harness/export.py
"""One JSONL row per episode, from an Inspect log: the table the analysis reads. Transcripts stay in the log."""
import json
from pathlib import Path

from inspect_ai.log import EvalLog

from orbitbench.harness.claims import answer_of, false_claims, trace_of


def providers_of(sample) -> str:
    """The inference providers that served the model calls of an episode, sorted and joined by '|' (OpenRouter names the
    provider in each raw response). Empty when the log has none (a model that is not served through OpenRouter)."""
    names = {e.call.response.get("provider") for e in sample.events or []
             if e.event == "model" and e.call and isinstance(e.call.response, dict) and e.call.response.get("provider")}
    return "|".join(sorted(names))


def settings_of(log: EvalLog) -> dict:
    """What the run was played with, so that a row says it: sampling settings the provider was given (None is unset;
    an unset temperature is the provider's default, written as such), the declared limits and the harness version."""
    gen, cfg = log.eval.model_generate_config, log.eval.config
    return {"temperature": "provider_default" if gen.temperature is None else gen.temperature,
            "top_p": gen.top_p, "max_tokens": gen.max_tokens, "reasoning_effort": gen.reasoning_effort,
            "batch": bool(gen.batch), "message_limit": cfg.message_limit, "token_limit": cfg.token_limit,
            "epochs": cfg.epochs, "inspect_ai": log.eval.packages.get("inspect_ai"),
            "provider_requested": (log.eval.model_args or {}).get("provider")}


def rows_of(log: EvalLog, condition: str) -> list[dict]:
    settings = settings_of(log)
    rows = []
    for sample in log.samples or []:
        family, mode, seed = sample.id.split(":")
        score = sample.scores.get("orbitbench_scorer") if sample.scores else None
        outcome = score.metadata["outcome"] if score else None
        if sample.limit is not None:
            outcome = f"limit_{sample.limit.type}"       # the reply was cut short: the label says why
        elif sample.error is not None:
            outcome = "error"
        claims = false_claims(trace_of(sample.messages), answer_of(sample.output.completion), outcome)
        usage = list((sample.model_usage or {}).values())
        rows.append({
            "id": sample.id, "family": family, "mode": mode, "seed": int(seed), "epoch": sample.epoch, "condition": condition,
            "model": log.eval.model, **settings, "providers": providers_of(sample), "outcome": outcome,
            "solved": score.value["solved"] if score else 0.0, "reward": score.value["reward"] if score else 0.0,
            "assistant_turns": sum(m.role == "assistant" for m in sample.messages),
            "tool_calls": sum(m.role == "tool" for m in sample.messages),
            # the calls to the tools of the gmat server: every tool but the Python interpreter
            "gmat_calls": sum(tc.function != "python" for m in sample.messages if m.role == "assistant"
                              for tc in m.tool_calls or []),
            # input_tokens excludes the cached ones: the whole input is the three columns together
            "input_tokens": sum(u.input_tokens for u in usage),
            "cache_write_tokens": sum(u.input_tokens_cache_write or 0 for u in usage),
            "cache_read_tokens": sum(u.input_tokens_cache_read or 0 for u in usage),
            "output_tokens": sum(u.output_tokens for u in usage),
            "total_time_s": sample.total_time, "working_time_s": sample.working_time,
            **claims,
            "error": sample.error.message[:500] if sample.error else None,
        })
    return rows


def write_jsonl(logs: list[EvalLog], condition: str, path: Path) -> int:
    rows = [row for log in logs for row in rows_of(log, condition)]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return len(rows)
