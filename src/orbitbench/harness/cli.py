# src/orbitbench/harness/cli.py
"""python -m orbitbench.harness run --condition B --model anthropic/claude-haiku-5-5 --log-dir runs/pilot-b
python -m orbitbench.harness report runs/pilot-b runs/pilot-c"""
import argparse
from pathlib import Path

from orbitbench.harness.catalog import V01_LINES, instances


def parse(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="orbitbench.harness")
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a model on instances; an interrupted run resumes when relaunched")
    run.add_argument("--condition", choices=["A", "B", "C"], required=True)
    run.add_argument("--model", required=True, help="an Inspect model name, e.g. anthropic/claude-haiku-5-5")
    run.add_argument("--log-dir", required=True, type=Path, help="one folder per run: relaunching resumes it")
    run.add_argument("--families", nargs="*", help="only these families (default: all of v0.1)")
    run.add_argument("--first-seed", type=int, default=0, help="each line uses seeds first-seed .. first-seed+n-1")
    run.add_argument("--per-line", type=int, help="at most this many seeds per line (default: all of the line)")
    run.add_argument("--max-level", type=int, help="only instances up to this level (default: 2 for condition A)")
    run.add_argument("--max-samples", type=int, default=4, help="episodes in parallel")
    run.add_argument("--limit", type=int, help="only the first N episodes (smoke tests)")
    run.add_argument("--token-limit", type=int, help="spending guard: tokens allowed to one episode")
    run.add_argument("--epochs", type=int, default=1, help="plays of each instance (reliability needs at least 2)")
    run.add_argument("--batch", action="store_true",
                     help="use the Message Batches API: half the price, but every turn waits for its batch")
    report = sub.add_parser("report", help="table, token bill and failures to audit, from the episodes.jsonl of runs")
    report.add_argument("dirs", nargs="+", type=Path)
    analyze = sub.add_parser("analyze", help="success rates with intervals and the C minus B difference, from runs")
    analyze.add_argument("dirs", nargs="+", type=Path)
    return p.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    from inspect_ai import eval_set
    from inspect_ai.log import read_eval_log

    from orbitbench.harness.export import write_jsonl
    from orbitbench.harness.report import load, render
    from orbitbench.harness.task import build_task

    lines = [ln for ln in V01_LINES if not args.families or ln[0] in args.families]
    if not lines:
        raise SystemExit(f"no line matches {args.families}")
    task = build_task(instances(lines, args.first_seed, args.per_line, args.max_level or (2 if args.condition == "A" else None)), args.condition, token_limit=args.token_limit,
                      epochs=args.epochs)
    success, logs = eval_set(task, log_dir=str(args.log_dir), model=args.model, max_samples=args.max_samples,
                             limit=args.limit, display="plain", retry_attempts=2, batch=args.batch or None)
    logs = [read_eval_log(log.location) for log in logs]     # eval_set returns the logs without their samples
    n = write_jsonl(logs, args.condition, args.log_dir / "episodes.jsonl")
    print(f"{n} episodes written to {args.log_dir / 'episodes.jsonl'}; complete: {success}")
    print(render(load([args.log_dir])))
    return 0 if success else 1


def report(args: argparse.Namespace) -> int:
    from orbitbench.harness.report import load, render
    print(render(load(args.dirs)))
    return 0


def analyze(args: argparse.Namespace) -> int:
    from orbitbench.harness.analysis import analyze as render_analysis
    print(render_analysis(args.dirs))
    return 0


def main(argv=None) -> int:
    args = parse(argv)
    return {"run": run, "report": report, "analyze": analyze}[args.command](args)
