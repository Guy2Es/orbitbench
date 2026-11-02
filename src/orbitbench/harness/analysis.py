# src/orbitbench/harness/analysis.py
"""The numbers of the write-up, from the episodes.jsonl of runs: success rates with Wilson intervals, and the
difference between conditions on the same instances with a paired hierarchical bootstrap (families, then instances),
reliability over repeated plays, and the rates of false claims. Instance ids pair the episodes and are never
printed."""
import math
import random
from collections import defaultdict

from orbitbench.harness.claims import FLAGS
from orbitbench.harness.report import TOKEN_KINDS, load

Z95 = 1.959964


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def paired_bootstrap(diffs: list[float], n_boot: int = 10000, seed: int = 0) -> tuple[float, float, float]:
    """Mean of the paired differences and its 95 % percentile bootstrap interval (instances resampled)."""
    n = len(diffs)
    rng = random.Random(seed)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return (sum(diffs) / n, means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1])


def hierarchical_bootstrap(groups: dict, n_boot: int = 10000, seed: int = 0) -> tuple[float, float, float]:
    """Mean over all instances and its 95 % percentile interval. `groups` maps a family to the values of its
    instances; each replicate resamples the families, then the instances inside each drawn family."""
    names = sorted(groups)
    rng = random.Random(seed)
    values = [v for name in names for v in groups[name]]
    means = []
    for _ in range(n_boot):
        drawn = [v for name in (names[rng.randrange(len(names))] for _ in names)
                 for v in (groups[name][rng.randrange(len(groups[name]))] for _ in groups[name])]
        means.append(sum(drawn) / len(drawn))
    means.sort()
    return (sum(values) / len(values), means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1])


def _by_family(ids, value) -> dict:
    groups: dict[str, list[float]] = defaultdict(list)
    for i in ids:
        groups[i.split(":")[0]].append(value(i))
    return dict(groups)


def _collapse(rows: list[dict]) -> list[dict]:
    """One row per (model, condition, instance): the plays of an instance averaged. `epochs` counts them and `all_solved`
    is whether every one succeeded."""
    plays: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        plays[(r["model"], r["condition"], r["id"])].append(r)
    out = []
    for rs in plays.values():
        n = len(rs)
        merged = {**rs[0], "epochs": n, "all_solved": all(r["solved"] == 1.0 for r in rs)}
        for key in ("solved", "reward", "assistant_turns"):
            merged[key] = sum(r[key] for r in rs) / n
        for key in (*TOKEN_KINDS, "gmat_calls"):
            merged[key] = sum(r.get(key, 0) for r in rs)
        out.append(merged)
    return out


def _split(rows: list[dict]) -> dict[tuple[str, str], dict[str, dict]]:
    """{(model, condition): {instance id: row}}."""
    out: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for r in rows:
        out[(r["model"], r["condition"])][r["id"]] = r
    return dict(out)


def _pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def render(rows: list[dict]) -> str:
    episodes = rows
    rows = _collapse(rows)
    groups = _split(rows)
    out = ["Success rate (every constraint of the reply met), 95 % Wilson interval", ""]
    out.append(f"{'model':30} {'cond':4} {'n':>3} {'solved':>7} {'interval':>14} {'reward':>7} {'turns':>6} {'gmat calls':>10}")
    for (model, cond), eps in sorted(groups.items()):
        rs = list(eps.values())
        n = sum(r["epochs"] for r in rs)
        k = round(sum(r["solved"] * r["epochs"] for r in rs))
        lo, hi = wilson(k, n)
        out.append(f"{model:30} {cond:4} {n:>3} {f'{k}/{n}':>7} {f'{_pct(lo)} to {_pct(hi)}':>14} "
                   f"{sum(r['reward'] * r['epochs'] for r in rs) / n:>7.2f} "
                   f"{sum(r['assistant_turns'] * r['epochs'] for r in rs) / n:>6.1f} "
                   f"{sum(r.get('gmat_calls', 0) for r in rs):>10}")
    out += ["", "Condition C minus condition B, on the same instances (paired hierarchical bootstrap, 95 % interval)", ""]
    out.append(f"{'model':30} {'pairs':>5} {'solved':>8} {'interval':>16} {'reward':>8} {'interval':>16}")
    for model in sorted({m for m, _ in groups}):
        b, c = groups.get((model, "B"), {}), groups.get((model, "C"), {})
        ids = sorted(set(b) & set(c))
        if not ids:
            continue
        ds = hierarchical_bootstrap(_by_family(ids, lambda i: c[i]["solved"] - b[i]["solved"]))
        dr = hierarchical_bootstrap(_by_family(ids, lambda i: c[i]["reward"] - b[i]["reward"]))
        out.append(f"{model:30} {len(ids):>5} {ds[0]:>+8.3f} {f'{ds[1]:+.3f} to {ds[2]:+.3f}':>16} "
                   f"{dr[0]:>+8.3f} {f'{dr[1]:+.3f} to {dr[2]:+.3f}':>16}")
    out += ["", "By line: solved / instances", ""]
    keys = sorted(groups)
    out.append(f"{'line':42} " + " ".join(f"{m.split('/')[-1][:14] + ' ' + c:>20}" for m, c in keys))
    for fam, mode in sorted({(r["family"], r["mode"]) for r in rows}):
        cells = []
        for key in keys:
            rs = [r for r in groups[key].values() if (r["family"], r["mode"]) == (fam, mode)]
            cells.append(f"{sum(r['solved'] for r in rs):g}/{len(rs)}")
        out.append(f"{fam + '/' + mode:42} " + " ".join(f"{c:>20}" for c in cells))
    out += ["", "Tokens (uncached input, cache writes, cache reads, output) per model and condition", ""]
    for (model, cond), eps in sorted(groups.items()):
        t = {k: sum(r.get(k, 0) for r in eps.values()) for k in TOKEN_KINDS}
        out.append(f"{model} {cond}: " + ", ".join(f"{t[k]} {k.removesuffix('_tokens')}" for k in TOKEN_KINDS))
    if any(r["epochs"] > 1 for r in rows):
        out += ["", "Reliability: instances solved in every one of their plays (hierarchical bootstrap, 95 % interval)", ""]
        out.append(f"{'model':30} {'cond':4} {'plays':>5} {'instances':>9} {'all solved':>11} {'interval':>16}")
        for (model, cond), eps in sorted(groups.items()):
            m = hierarchical_bootstrap(_by_family(list(eps), lambda i: float(eps[i]["all_solved"])))
            plays = max(r["epochs"] for r in eps.values())
            out.append(f"{model:30} {cond:4} {plays:>5} {len(eps):>9} {m[0]:>11.3f} {f'{m[1]:.3f} to {m[2]:.3f}':>16}")
    if any("claimed_verified" in r for r in episodes):
        out += ["", "False claims (episodes flagged / episodes; rules in harness/claims.py)", ""]
        out.append(f"{'model':30} {'cond':4} {'episodes':>8} {'claimed ok':>10} " + " ".join(f"{f:>18}" for f in FLAGS))
        by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in episodes:
            by_key[(r["model"], r["condition"])].append(r)
        for (model, cond), rs in sorted(by_key.items()):
            out.append(f"{model:30} {cond:4} {len(rs):>8} {sum(bool(r.get('claimed_verified')) for r in rs):>10} "
                       + " ".join(f"{sum(bool(r.get(f)) for r in rs):>18}" for f in FLAGS))
    outcomes: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in episodes:
        outcomes[(r["model"], r["condition"])][r["outcome"]] += 1
    out += ["", "Outcomes", ""]
    for (model, cond), counts in sorted(outcomes.items()):
        out.append(f"{model} {cond}: " + ", ".join(f"{o}:{n}" for o, n in sorted(counts.items())))
    return "\n".join(out)


def analyze(dirs) -> str:
    return render(load(dirs))
