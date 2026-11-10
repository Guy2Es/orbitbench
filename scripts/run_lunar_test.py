# scripts/run_lunar_test.py
"""The run on the private lunar test seeds, step by step (model, condition), cheapest first, under a spending ceiling.

Before each step the OpenRouter account's total usage is read; a step starts only if the spend since the run began plus
the upper-bound cost of that step stays under the ceiling. Interrupted runs resume: relaunch the same command.
Usage: python scripts/run_lunar_test.py --ceiling 8.0
Needs OPENROUTER_API_KEY in .env, and private/lunar_test_range.txt and private/lunar_impact_table.yaml."""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# (short name, OpenRouter model, pinned provider or None, upper-bound USD of one condition over 90 episodes, cache read at
# the full input price: docs/freeze.md, v1.1). Order: cheapest first.
MODELS = [
    ("gptoss", "openai/gpt-oss-120b", "Crusoe", {"B": 0.01, "C": 0.30}),
    ("geminilite", "google/gemini-2.5-flash-lite", None, {"B": 0.05, "C": 0.70}),
    ("qwenflash", "qwen/qwen3.7-flash", None, {"B": 0.95, "C": 1.00}),
]


def api_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("OPENROUTER_API_KEY is not in .env")


def total_usage(key: str) -> float:
    req = urllib.request.Request("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return float(json.load(r)["data"]["total_usage"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ceiling", type=float, required=True, help="USD, spent since the run began")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--max-samples", type=int, default=3)
    ap.add_argument("--models", default="", help="comma-separated short names (default: all, in order)")
    args = ap.parse_args()
    first = int((ROOT / "private" / "lunar_test_range.txt").read_text().split("-")[0])
    key = api_key()
    state_path = ROOT / "private" / "lunar_test_run.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"start_usage": total_usage(key), "done": []}
    state_path.write_text(json.dumps(state))
    wanted = set(filter(None, args.models.split(",")))
    for short, model, provider, bounds in MODELS:
        if wanted and short not in wanted:
            continue
        for cond, bound in bounds.items():
            step = f"{short}-{cond}"
            if step in state["done"]:
                continue
            spent = total_usage(key) - state["start_usage"]
            print(f"[{step}] spent {spent:.3f} USD, upper bound of this step {bound:.2f}, ceiling {args.ceiling:.2f}", flush=True)
            if spent + bound > args.ceiling:
                print(f"[{step}] NOT STARTED: it could cross the ceiling. Stopping.", flush=True)
                return 2
            cmd = [sys.executable, "-m", "orbitbench.harness", "run", "--condition", cond, "--suite", "lunar_test",
                   "--first-seed", str(first), "--epochs", str(args.epochs), "--max-samples", str(args.max_samples),
                   "--token-limit", "1000000", "--deny-data-collection", "--model", f"openrouter/{model}",
                   "--log-dir", str(ROOT / "runs" / f"lunar-test-{short}-{cond}")]
            if provider:
                cmd += ["--provider", provider]
            code = subprocess.call(cmd, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"})
            after = total_usage(key) - state["start_usage"]
            print(f"[{step}] finished with code {code}; spent so far {after:.3f} USD", flush=True)
            if code != 0:
                print(f"[{step}] incomplete: relaunch this command to resume, or look at the log.", flush=True)
                return 1
            state["done"].append(step)
            state_path.write_text(json.dumps(state))
    print("all steps done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
