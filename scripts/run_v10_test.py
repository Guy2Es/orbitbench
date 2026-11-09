# scripts/run_v10_test.py
"""The v1.0 run on the private test seeds, step by step (model, condition, suite), cheapest first, under a spending ceiling.

Three models (gpt-oss-120b, Gemini 2.5 Flash Lite, Qwen3.7 Flash), conditions A, B and C, 5 seeds per line, one attempt.
Suites of each step: `v10` (79 instances, A plays the 34 of levels 1 and 2), `twins` (9) and `canary` (3).
DeepSeek V4 Flash is not part of this run (docs/freeze.md, 9 November 2026).

Before each step the OpenRouter account's total usage is read; a step starts only if the spend since the run began plus
the upper bound of that step stays under the ceiling. Interrupted runs resume: relaunch the same command.
The first test seed is read from ORBITBENCH_TEST_FIRST_SEED_V10 in .env and is never printed.
Usage: python scripts/run_v10_test.py --ceiling <USD> [--dry-run]
`--dry-run` prints the plan and the upper bounds, reads nothing from the account and starts nothing."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_lunar_test import api_key, total_usage  # noqa: E402
from orbitbench.harness.catalog import CANARY_LINES, TWIN_LINES, V10_LINES, instances  # noqa: E402

PER_LINE = 5
SAFETY = 1.25    # on the measured upper bound per instance: 17 pilot episodes per cell, a small sample
SUITES = (("v10", V10_LINES), ("twins", TWIN_LINES), ("canary", CANARY_LINES))
# (short name, OpenRouter model, pinned provider or None, upper bound of USD per instance by condition).
# B and C: measured on the v1.0 sample of 8 November 2026 (cache read at the full input price). A: an assumption (no
# tool, short replies), not measured; it is checked against the account after the first A step.
MODELS = [
    ("gptoss", "openai/gpt-oss-120b", "Crusoe", {"A": 0.0003, "B": 0.0004, "C": 0.0012}),
    ("geminilite", "google/gemini-2.5-flash-lite", None, {"A": 0.0008, "B": 0.0025, "C": 0.0085}),
    ("qwenflash", "qwen/qwen3.7-flash", None, {"A": 0.0030, "B": 0.0061, "C": 0.0085}),
]


def env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit(f"{name} is not in .env")


def plan(models=MODELS):
    """Every step in order: (name, short, model, provider, condition, suite, instances, upper bound in USD)."""
    steps = []
    counts = {}    # generating an instance is slow: count once per (condition, suite), not once per model
    for short, model, provider, per_instance in models:
        for cond in ("A", "B", "C"):
            for suite, lines in SUITES:
                if (cond, suite) not in counts:
                    counts[(cond, suite)] = len(instances(lines, 0, PER_LINE, 2 if cond == "A" else None))
                n = counts[(cond, suite)]
                steps.append((f"{short}-{cond}-{suite}", short, model, provider, cond, suite, n,
                              n * per_instance[cond] * SAFETY))
    return steps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ceiling", type=float, required=True, help="USD, spent since the run began")
    ap.add_argument("--max-samples", type=int, default=3)
    ap.add_argument("--models", default="", help="comma-separated short names (default: all, in order)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and the bounds, start nothing")
    args = ap.parse_args()
    wanted = set(filter(None, args.models.split(",")))
    steps = [s for s in plan() if not wanted or s[1] in wanted]
    if args.dry_run:
        for name, _, _, _, _, _, n, bound in steps:
            print(f"{name:28s} {n:3d} instances  upper bound {bound:.3f} USD")
        print(f"total upper bound {sum(s[-1] for s in steps):.2f} USD, ceiling {args.ceiling:.2f}")
        return 0
    first = int(env_value("ORBITBENCH_TEST_FIRST_SEED_V10"))
    key = api_key()
    state_path = ROOT / "private" / "v10_test_run.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"start_usage": total_usage(key), "done": []}
    state_path.write_text(json.dumps(state))
    for name, short, model, provider, cond, suite, _, bound in steps:
        if name in state["done"]:
            continue
        spent = total_usage(key) - state["start_usage"]
        print(f"[{name}] spent {spent:.3f} USD, upper bound of this step {bound:.3f}, ceiling {args.ceiling:.2f}", flush=True)
        if spent + bound > args.ceiling:
            print(f"[{name}] NOT STARTED: it could cross the ceiling. Stopping.", flush=True)
            return 2
        cmd = [sys.executable, "-m", "orbitbench.harness", "run", "--condition", cond, "--suite", suite,
               "--first-seed", str(first), "--per-line", str(PER_LINE), "--epochs", "1",
               "--max-samples", str(args.max_samples), "--token-limit", "1000000", "--deny-data-collection",
               "--model", f"openrouter/{model}", "--log-dir", str(ROOT / "runs" / f"v10-test-{short}-{cond}-{suite}")]
        if provider:
            cmd += ["--provider", provider]
        code = subprocess.call(cmd, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"})
        after = total_usage(key) - state["start_usage"]
        print(f"[{name}] finished with code {code}; spent so far {after:.3f} USD", flush=True)
        if code != 0:
            print(f"[{name}] incomplete: relaunch this command to resume, or look at the log.", flush=True)
            return 1
        state["done"].append(name)
        state_path.write_text(json.dumps(state))
    print("all steps done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
