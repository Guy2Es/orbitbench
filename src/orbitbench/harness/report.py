# src/orbitbench/harness/report.py
"""Reads the episodes.jsonl of runs: a table per line, the token bill, and the failures to audit."""
import json
from collections import Counter, defaultdict
from pathlib import Path


def load(dirs: list[Path]) -> list[dict]:
    rows = []
    for d in dirs:
        for line in (d / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
            rows.append({**json.loads(line), "run": str(d)})
    return rows


TOKEN_KINDS = ("input_tokens", "cache_write_tokens", "cache_read_tokens", "output_tokens")


def tokens(rows: list[dict]) -> dict[str, dict[str, int]]:
    """Tokens per model and kind: uncached input, cache writes, cache reads, output (the four are billed apart)."""
    total: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(TOKEN_KINDS, 0))
    for r in rows:
        for kind in TOKEN_KINDS:
            total[r["model"]][kind] += r.get(kind, 0)
    return dict(total)


def table(rows: list[dict]) -> str:
    groups = defaultdict(list)
    for r in rows:
        groups[(r["condition"], r["model"], r["family"], r["mode"])].append(r)
    out = [f"{'cond':4} {'model':30} {'line':34} {'n':>3} {'solved':>6} {'reward':>6} {'turns':>5} {'tokens':>8}  outcomes"]
    for (cond, model, family, mode), rs in sorted(groups.items()):
        n = len(rs)
        outcomes = ", ".join(f"{k}:{v}" for k, v in sorted(Counter(r["outcome"] for r in rs).items()))
        out.append(f"{cond:4} {model:30} {family + '/' + mode:34} {n:>3} {sum(r['solved'] for r in rs) / n:>6.2f} "
                   f"{sum(r['reward'] for r in rs) / n:>6.2f} {sum(r['assistant_turns'] for r in rs) / n:>5.1f} "
                   f"{sum(sum(r.get(k, 0) for k in TOKEN_KINDS) for r in rs) // n:>8}  {outcomes}")
    return "\n".join(out)


def failures(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["solved"] < 1.0]


def render(rows: list[dict]) -> str:
    bad = failures(rows)
    out = [table(rows), "", f"{len(rows)} episodes, {len(bad)} not solved"]
    for model, t in sorted(tokens(rows).items()):
        out.append(f"tokens {model}: " + ", ".join(f"{t[k]} {k.removesuffix('_tokens')}" for k in TOKEN_KINDS))
    out += ["", "to audit (run, id, condition, outcome):"]
    out += [f"  {r['run']}  {r['id']}  {r['condition']}  {r['outcome']}" for r in bad]
    return "\n".join(out)
