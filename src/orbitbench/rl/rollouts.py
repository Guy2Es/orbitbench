# src/orbitbench/rl/rollouts.py
"""From played episodes to fine-tuning data (reward-filtered self-training, docs/rl_plan.md, amendment of 12 Nov 2026).

An episode is one row of the harness export plus the transcript as chat messages, the tools the model was given, whether its
final reply parses, and the token count of the first prompt (the Colab side checks that its own rendering of the chat has the
same count). `select` keeps, per arm, at most two replies per instance; `write_sft` writes them with a manifest and a hash.
Nothing here trains or serves a model."""
import hashlib
import json
import random
from pathlib import Path

from orbitbench.harness.export import rows_of
from orbitbench.rl.reward import format_ok

MAX_PER_INSTANCE = 2


def _tool_spec(info) -> dict:
    return {"type": "function", "function": {"name": info.name, "description": info.description,
                                             "parameters": info.parameters.model_dump(exclude_none=True)}}


def _resolve(obj, attachments: dict):
    """Inspect's log keeps long texts of its events (a tool's description) as `attachment://<id>`: put the text back."""
    if isinstance(obj, str) and obj.startswith("attachment://"):
        return attachments.get(obj.removeprefix("attachment://"), obj)
    if isinstance(obj, dict):
        return {k: _resolve(v, attachments) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve(v, attachments) for v in obj]
    return obj


def sent_tools(sample, first) -> list[dict]:
    """The tools exactly as the first request carried them (the server renders what it receives, `strict` included),
    with their attachments resolved; the tool info of the event when the log holds no request (a mock model)."""
    call = getattr(first, "call", None)
    request = call.request if call is not None and isinstance(call.request, dict) else {}
    tools = request.get("tools") or [_tool_spec(t) for t in (first.tools if first else [])]
    tools = _resolve(tools, sample.attachments or {})
    if "attachment://" in json.dumps(tools):
        raise ValueError("a tool description is still an attachment reference: the log cannot be turned into training data")
    return tools


def _chat(message) -> dict:
    """One Inspect message as the dict a chat template reads (assistant tool calls carry their arguments as a dict)."""
    if message.role == "assistant":
        out = {"role": "assistant", "content": message.text}
        if message.tool_calls:
            out["tool_calls"] = [{"id": tc.id, "type": "function", "function": {"name": tc.function, "arguments": tc.arguments}}
                                 for tc in message.tool_calls]
        return out
    if message.role == "tool":
        return {"role": "tool", "tool_call_id": message.tool_call_id, "name": message.function, "content": message.text}
    return {"role": message.role, "content": message.text}


def _input_tokens(usage) -> int:
    """Every input token of one model call: a server may count the cached ones apart."""
    return usage.input_tokens + (usage.input_tokens_cache_read or 0) + (usage.input_tokens_cache_write or 0)


def _usages(sample) -> list:
    return [e.output.usage for e in sample.events or [] if e.event == "model" and e.output and e.output.usage]


def first_prompt_tokens(sample) -> int | None:
    """Input tokens the server counted for the first model call of an episode (system message, tools and statement)."""
    usages = _usages(sample)
    return _input_tokens(usages[0]) if usages else None


def context_tokens(sample) -> int | None:
    """Length of the whole transcript as the server counted it: the input and the output of the last model call."""
    usages = _usages(sample)
    return _input_tokens(usages[-1]) + usages[-1].output_tokens if usages else None


def episodes_of(log, condition: str) -> list[dict]:
    """One dict per episode of an Inspect log: the harness row, plus `messages`, `tools`, `completion`, `format_ok`,
    `prompt_tokens` (first prompt) and `context_tokens` (whole transcript)."""
    samples = log.samples or []
    out = []
    for row, sample in zip(rows_of(log, condition), samples):
        first = next((e for e in sample.events or [] if e.event == "model"), None)
        completion = sample.output.completion if sample.output else ""
        out.append({**row, "messages": [_chat(m) for m in sample.messages],
                    "tools": sent_tools(sample, first),
                    "completion": completion, "format_ok": format_ok(completion), "prompt_tokens": first_prompt_tokens(sample),
                    "context_tokens": context_tokens(sample)})
    return out


def episodes_from_dir(log_dir, condition: str) -> list[dict]:
    """Every episode of the finished logs (`*.eval`) in a run folder; logs that did not finish are ignored."""
    from inspect_ai.log import read_eval_log
    out = []
    for path in sorted(Path(log_dir).glob("*.eval")):
        log = read_eval_log(str(path))
        if log.status == "success":
            out += episodes_of(log, condition)
    return out


def _per_instance(episodes: list[dict], cap: int, order) -> list[dict]:
    """At most `cap` episodes of each instance, taking them in the order `order(episodes of one instance)` gives."""
    by_id: dict[str, list[dict]] = {}
    for e in episodes:
        by_id.setdefault(e["id"], []).append(e)
    return [e for i in sorted(by_id) for e in order(by_id[i])[:cap]]


def too_long(episode: dict, max_tokens: int | None) -> bool:
    """True if the transcript is known to exceed `max_tokens` (an episode with no token count is never too long)."""
    return max_tokens is not None and (episode.get("context_tokens") or 0) > max_tokens


def select(episodes: list[dict], seed: int = 0, cap: int = MAX_PER_INSTANCE, count: int | None = None,
           max_tokens: int | None = None) -> dict[str, list[dict]]:
    """The two training sets of one round.
    `reward`: replies the grader rewards (reward 1.0, nothing added), at most `cap` per instance, shortest first.
    `format`: replies whose final block parses, right or wrong, at most `cap` per instance drawn at random, then drawn at
    random again down to the number of `reward` replies, so that both sets have the same size. `count` sets that size when
    the two sets come from different models (round 1: the format arm plays its own block, and matches the reward arm's count).
    `max_tokens`: transcripts longer than this are in neither set (the fine-tune could not hold them), and they are removed
    before the sizes are matched, so that the fine-tune drops nothing and the arms stay the same size."""
    rng = random.Random(seed)
    episodes = [e for e in episodes if not too_long(e, max_tokens)]
    rewarded = _per_instance([e for e in episodes if e["reward"] >= 1.0],
                             cap, lambda es: sorted(es, key=lambda e: (e["output_tokens"], e["epoch"])))
    parsing = _per_instance([e for e in episodes if e["format_ok"]], cap, lambda es: rng.sample(es, len(es)))
    target = len(rewarded) if count is None else count
    parsing = sorted(rng.sample(parsing, min(target, len(parsing))), key=lambda e: (e["id"], e["epoch"]))
    return {"reward": rewarded, "format": parsing}


def write_sft(episodes: list[dict], path, *, arm: str, round_: int, train_seed: int, note: str = "") -> dict:
    """Write the kept episodes as JSONL (id, epoch, reward, messages, tools, prompt_tokens, context_tokens) and
    `<path>.manifest.json` with the counts and the SHA-256 of the data file. Returns the manifest."""
    path = Path(path)
    rows = [{"id": e["id"], "epoch": e["epoch"], "reward": e["reward"], "messages": e["messages"], "tools": e["tools"],
             "prompt_tokens": e.get("prompt_tokens"), "context_tokens": e.get("context_tokens")} for e in episodes]
    data = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows).encode("utf-8")
    path.write_bytes(data)
    manifest = {"file": path.name, "sha256": hashlib.sha256(data).hexdigest(), "arm": arm, "round": round_,
                "train_seed": train_seed, "examples": len(rows), "instances": len({r["id"] for r in rows}),
                "output_tokens": sum(e.get("output_tokens", 0) for e in episodes), "note": note}
    Path(str(path) + ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def read_sft(path) -> list[dict]:
    """The rows of a file written by `write_sft` (to add the rounds together before a fine-tune)."""
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
