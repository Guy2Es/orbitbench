# scripts/estimate_cost.py
"""Estimates what a planned run costs, from the tokens that sample episodes used.

Input: JSONL rows with model, family, mode and the four token columns of an Inspect `episodes.jsonl` (input_tokens,
cache_write_tokens, cache_read_tokens, output_tokens). The plan is the v1.0 default suite (85 instances, 9 twins,
3 canaries) in conditions B and C, condition A on levels 1 and 2, times k attempts per model."""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

from orbitbench.harness.catalog import CANARY_LINES, TWIN_LINES, V10_LINES, instances

# USD per million tokens (input, output, cache read, cache write). Haiku: prompts up to 100K tokens. Opus cache write
# is assumed at 1.25x its input price, like the other two: not read from a price page.
PRICES = {"haiku": (0.10, 0.50, 0.01, 0.125), "sonnet": (2.0, 10.0, 0.20, 2.5), "opus": (4.0, 20.0, 0.20, 5.0)}
BATCH_FACTOR = 0.5
COLUMNS = ("input_tokens", "cache_write_tokens", "cache_read_tokens", "output_tokens")


def family_of(model: str) -> str:
    found = re.search(r"haiku|sonnet|opus", model.lower())
    if not found:
        raise ValueError(f"no price for model {model!r}")
    return found.group(0)


def usd(row: dict, model: str) -> float:
    p_in, p_out, p_read, p_write = PRICES[model]
    return (row["input_tokens"] * p_in + row["output_tokens"] * p_out + row["cache_read_tokens"] * p_read
            + row["cache_write_tokens"] * p_write) / 1e6


def load(paths) -> list[dict]:
    rows = []
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if all(row.get(c) is not None for c in COLUMNS):
                    rows.append(row)
    return rows


def profile(rows: list[dict]) -> dict:
    """Mean cost per episode, by (model, condition, family:mode), with the means by (model, condition) as a fallback."""
    cell, coarse = defaultdict(list), defaultdict(list)
    for r in rows:
        model = family_of(r["model"])
        cost = usd(r, model)
        cell[(model, r["condition"], f"{r['family']}:{r['mode']}")].append(cost)
        coarse[(model, r["condition"])].append(cost)
    return {"cell": {k: sum(v) / len(v) for k, v in cell.items()},
            "coarse": {k: sum(v) / len(v) for k, v in coarse.items()},
            "n_cell": {k: len(v) for k, v in cell.items()}, "n_coarse": {k: len(v) for k, v in coarse.items()}}


def plan_lines():
    return instances(V10_LINES) + instances(TWIN_LINES) + instances(CANARY_LINES)


def estimate(rows, models, k, fraction, batch, margin):
    prof, suite = profile(rows), plan_lines()
    out, total = [], 0.0
    for model in models:
        spent, episodes, fallback = 0.0, 0, 0
        for cond in ("A", "B", "C"):
            if (model, cond) not in prof["coarse"]:
                continue
            for inst in suite:
                if cond == "A" and inst.level > 2:
                    continue
                key = (model, cond, f"{inst.family}:{inst.mode}")
                cost = prof["cell"].get(key)
                if cost is None:
                    cost, fallback = prof["coarse"][(model, cond)], fallback + 1
                spent += cost * k * (fraction if model == "opus" else 1.0)
                episodes += k * (fraction if model == "opus" else 1.0)
        if batch:
            spent *= BATCH_FACTOR
        out.append((model, round(episodes), spent, fallback))
        total += spent
    return out, total, total * margin


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", nargs="+", required=True)
    ap.add_argument("--models", nargs="+", default=["haiku", "sonnet", "opus"], choices=list(PRICES))
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--opus-fraction", type=float, default=0.3, help="share of the suite played by Opus")
    ap.add_argument("--no-batch", action="store_true")
    ap.add_argument("--margin", type=float, default=1.3)
    args = ap.parse_args(argv)
    rows = load(args.rows)
    out, total, with_margin = estimate(rows, args.models, args.k, args.opus_fraction, not args.no_batch, args.margin)
    prof = profile(rows)
    print(f"{len(rows)} sample episodes; batch {'off' if args.no_batch else 'on (-50 %)'}; k = {args.k}")
    for model, episodes, spent, fallback in out:
        print(f"  {model:7s} {episodes:5d} episodes  {spent:7.2f} USD  ({fallback} lines priced from the model's mean)")
    print(f"  total {total:.2f} USD; with a margin of {args.margin}: {with_margin:.2f} USD; "
          f"load at least {math.ceil(with_margin / 5) * 5} USD")
    thin = sorted(k for k, n in prof["n_coarse"].items() if n < 10)
    if thin:
        print(f"  warning: fewer than 10 sample episodes for {thin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
