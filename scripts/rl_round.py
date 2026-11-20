# scripts/rl_round.py
"""The local side of the RL study (docs/rl_plan.md, amendment of 12 November 2026): play through the real harness with a model
served by Ollama, then select the training replies of both arms. Nothing here trains a model (that is scripts/rl_finetune.py,
on Colab) and nothing downloads one. Condition B, spending guard of 60,000 tokens per episode, 60-message limit as frozen.

  python scripts/rl_round.py phase0 --name qwen3-4b --tag qwen3-4b-instruct-16k      # the 72 episodes of phase 0
  python scripts/rl_round.py bakeoff --finetune-ok qwen3-4b --parallel 8 --units-per-hour 1.5   # table, time and units of a block
  python scripts/rl_round.py play --arm base --tag <ollama tag> --train-seed 0 --round 0
  python scripts/rl_round.py select --train-seed 0 --round 0 --base-arm base          # both arms' SFT files, manifests
  python scripts/rl_round.py merge --train-seed 0 --arm reward                        # rounds 0 and 1 added, for the fine-tune
  python scripts/rl_round.py evaluate --arm base --tag <ollama tag>                   # suite rl on the private range

A run folder resumes when the same command is relaunched. Folders and data go under $RL_DIR (default runs/rl/, not versioned).
On Colab: `--server vllm --sandbox local` (a vLLM server on localhost:8000, VLLM_BASE_URL and VLLM_API_KEY set); the tag is the
name the server serves. Inspect's own `vllm/` provider is used, not `openai-api/`: it ends an episode that outgrows the 16k
context as `model_length`, where the generic provider raises an error that stops the block. At home the defaults are Ollama
and the frozen Docker sandbox. The final evaluation is always at home."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from orbitbench.harness.catalog import RL_HELD_OUT_LINES, RL_LINES  # noqa: E402
from orbitbench.rl.data import MAX_BLOCKS_R0, PHASE0_FIRST_SEED, block_first_seed  # noqa: E402
from orbitbench.rl.rollouts import episodes_from_dir, read_sft, select, too_long, write_sft  # noqa: E402

# Root of the run folders and training files: runs/rl at home; on Colab, set RL_DIR to the Drive folder (see rl_colab.py).
RL = Path(os.environ.get("RL_DIR", ROOT / "runs" / "rl"))
TOKEN_GUARD = 60_000          # tokens of one episode (input, cache-read and output), as written in docs/rl_plan.md
BLOCK_N = 144                 # distinct instances of a block; 96 if the chosen model needs more than 90 s per episode
ATTEMPTS = 4                  # per instance in a rollout block
MIN_REWARDED = 48             # fewer rewarded replies in round 0: play another round-0 block (MAX_BLOCKS_R0 blocks at most)
MAX_EXAMPLE_TOKENS = 8192     # longer transcripts are in neither arm's set: MAX_SEQ of rl_finetune.py (GPU memory)
BLOCKS = 9                    # 3 training seeds x (round 0 once, round 1 once per arm)
UNITS_CEILING = 150           # Colab compute units a month for the 9 blocks (rl_plan.md, amendment of 16 November 2026)
NUMBER_FAMILIES = ("hohmann", "plane_change_dv", "tsiolkovsky", "escape_velocity")
# The evaluation can be played in two parts so that the primary comparison (H6, the held-out plan families) comes first. The two
# held-out families have no other line, so a filter on family names splits the 138 instances exactly: 40 and 98.
HELD_OUT_FAMILIES = tuple(dict.fromkeys(f for f, _, _ in RL_HELD_OUT_LINES))
REST_FAMILIES = tuple(dict.fromkeys(f for f, _, _ in RL_LINES if f not in HELD_OUT_FAMILIES))
EVAL_PARTS = {"all": (None, ""), "held": (HELD_OUT_FAMILIES, "-held"), "rest": (REST_FAMILIES, "-rest")}


# ---- the rule of phase 0, fixed before any run (docs/rl_plan.md, section 3) -------------------------------------------

def phase0_row(name: str, episodes: list[dict], finetune_ok: bool) -> dict:
    """The bake-off line of one candidate from its 72 episodes. `finetune_ok`: a LoRA fine-tune and a GGUF export worked on a
    T4 (checked by hand, not measurable here). Eligible if all four conditions of the rule hold."""
    solved = [e for e in episodes if e["solved"] == 1.0]
    families = {e["family"] for e in solved if e["family"] in NUMBER_FAMILIES}
    hours = sum(e["total_time_s"] or 0 for e in episodes) / 3600
    row = {"name": name, "episodes": len(episodes), "solved": len(solved), "families_solved": len(families),
           "uses_tools": any(e["tool_calls"] > 0 for e in episodes),
           "thinking": any("<think" in (m.get("content") or "") for e in episodes for m in e["messages"]),
           "finetune_ok": finetune_ok, "gpu_hours": hours,
           "mean_s": 3600 * hours / len(episodes) if episodes else 0.0,
           "mean_output_tokens": sum(e["output_tokens"] for e in episodes) / len(episodes) if episodes else 0.0}
    row["solved_per_hour"] = len(solved) / hours if hours else 0.0
    row["eligible"] = row["uses_tools"] and not row["thinking"] and finetune_ok and row["families_solved"] >= 3
    return row


def choose(rows: list[dict], default: str = "qwen3-4b") -> str:
    """The eligible candidate with the most solved episodes per GPU-hour; the default model if none is eligible."""
    eligible = [r for r in rows if r["eligible"]]
    return max(eligible, key=lambda r: r["solved_per_hour"])["name"] if eligible else default


def block_estimate(row: dict, parallel: int, units_per_hour: float | None = None) -> dict:
    """Hours of one block of 144 x 4 episodes from a phase-0 line, and the Colab units of the 9 blocks. The wall-clock time
    of an episode is its own time divided by the episodes in parallel (an estimate: the end of a run does not fill every
    slot). `units_per_hour` is the rate Colab shows for the runtime; without it no units are given."""
    hours = row["gpu_hours"] / row["episodes"] / parallel * BLOCK_N * ATTEMPTS if row["episodes"] else 0.0
    return {"block_hours": hours, "units": BLOCKS * hours * units_per_hour if units_per_hour else None}


def render_bakeoff(rows: list[dict], default: str = "qwen3-4b", parallel: int = 1, units_per_hour: float | None = None) -> str:
    """The table and what the rules say. `parallel` = 1 is the home case (one episode at a time): the 90 s rule of
    12 November applies. With parallel episodes (Colab) the time of one episode is not comparable with it, and the block
    size follows the units rule of 16 November alone."""
    out = [f"{'candidate':18} {'eps':>4} {'solved':>6} {'fam':>3} {'tools':>5} {'think':>5} {'ft':>3} {'s/ep':>6} {'tok/ep':>7} "
           f"{'solved/h':>8} eligible"]
    for r in rows:
        out.append(f"{r['name']:18} {r['episodes']:>4} {r['solved']:>6} {r['families_solved']:>3} {str(r['uses_tools']):>5} "
                   f"{str(r['thinking']):>5} {str(r['finetune_ok']):>3} {r['mean_s']:>6.0f} {r['mean_output_tokens']:>7.0f} "
                   f"{r['solved_per_hour']:>8.1f} {r['eligible']}")
    pick = choose(rows, default)
    out += ["", f"choice by the rule: {pick}" + ("" if any(r["eligible"] for r in rows) else " (no candidate eligible: the default is kept)")]
    slow = next((r for r in rows if r["name"] == pick), None)
    if slow and parallel == 1 and slow["mean_s"] > 90:
        out.append(f"mean time per episode {slow['mean_s']:.0f} s > 90 s: the blocks are 96 instances x 4 attempts, not 144 x 4")
    if slow and parallel > 1:
        est = block_estimate(slow, parallel, units_per_hour)
        out.append(f"about {est['block_hours']:.1f} h for a block of {BLOCK_N} x {ATTEMPTS} episodes, {parallel} in parallel")
        if est["units"] is not None:
            rule = (f"at most {UNITS_CEILING}: blocks of {BLOCK_N} instances" if est["units"] <= UNITS_CEILING else
                    f"more than {UNITS_CEILING}: blocks of 96 instances x {ATTEMPTS} attempts, or the study over two months")
            out.append(f"about {est['units']:.0f} Colab units for the {BLOCKS} blocks, {rule}")
    return "\n".join(out)


# ---- running the harness ---------------------------------------------------------------------------------------------

def harness(cmd: list[str]) -> int:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    return subprocess.call([sys.executable, "-m", "orbitbench.harness", *cmd], cwd=ROOT, env=env)


def model_name(server: str, tag: str) -> str:
    """The Inspect model name: Ollama's tag, or a model served by a vLLM server that already runs (Inspect's `vllm/`
    provider connects to VLLM_BASE_URL with VLLM_API_KEY and starts nothing when the URL is set)."""
    return f"ollama/{tag}" if server == "ollama" else f"vllm/{tag}"


def samples_of(a) -> int:
    """Episodes in parallel: one for Ollama on the GTX 1070, eight for a vLLM server unless told otherwise."""
    return a.max_samples or (8 if a.server == "vllm" else 1)


def run_block(a, folder: Path, first_seed: int, n: int, epochs: int) -> int:
    return harness(["run", "--condition", "B", "--suite", "train", "--first-seed", str(first_seed), "--train-n", str(n),
                    "--epochs", str(epochs), "--max-samples", str(samples_of(a)), "--token-limit", str(TOKEN_GUARD),
                    "--sandbox", a.sandbox, "--model", model_name(a.server, a.tag), "--log-dir", str(folder)])


def block_dir(arm: str, t: int, r: int, d: int) -> Path:
    return RL / f"t{t}-r{r}-d{d}-{arm}"


def sft_path(arm: str, t: int, r: int) -> Path:
    return RL / "sft" / f"t{t}-r{r}-{arm}.jsonl"


def cmd_phase0(a) -> int:
    return run_block(a, RL / f"phase0-{a.name}", PHASE0_FIRST_SEED, 36, 2)


def cmd_bakeoff(a) -> int:
    ok = set(filter(None, a.finetune_ok.split(",")))
    rows = []
    for folder in sorted(RL.glob("phase0-*")):
        name = folder.name.removeprefix("phase0-")
        rows.append(phase0_row(name, episodes_from_dir(folder, "B"), name in ok))
    if not rows:
        raise SystemExit(f"no phase0-* folder in {RL}")
    print(render_bakeoff(rows, a.default, a.parallel, a.units_per_hour))
    return 0


def cmd_play(a) -> int:
    if a.first_seed is not None and a.arm in ("base", "reward", "format"):
        raise SystemExit("--first-seed is for smoke runs: give the folder another --arm name (a real arm plays its own block)")
    first = a.first_seed if a.first_seed is not None else block_first_seed(a.train_seed, a.round, a.redraw)
    return run_block(a, block_dir(a.arm, a.train_seed, a.round, a.redraw), first, a.block_n, ATTEMPTS)


def cmd_select(a) -> int:
    """The training files of one round, from the blocks played by the model named `--base-arm`. Round 0: the base model plays
    for both arms, run without `--only`. Round 1: each arm's own model plays its own block; run `--base-arm reward --only
    reward` first, then `--base-arm format --only format --count <examples of the reward file>` so that both arms keep the
    same number of examples."""
    t, r = a.train_seed, a.round
    episodes, played = [], []
    for d in range(MAX_BLOCKS_R0):
        folder = block_dir(a.base_arm, t, r, d)
        if folder.exists():
            episodes += episodes_from_dir(folder, "B")
            played.append(d)
    if not episodes:
        raise SystemExit(f"no episodes under {block_dir(a.base_arm, t, r, 0)}")
    chosen = select(episodes, seed=t, count=a.count, max_tokens=MAX_EXAMPLE_TOKENS)
    long = sum(too_long(e, MAX_EXAMPLE_TOKENS) for e in episodes if e["format_ok"])
    if long:
        print(f"{long} parsing replies longer than {MAX_EXAMPLE_TOKENS} tokens are in neither set")
    (RL / "sft").mkdir(parents=True, exist_ok=True)
    for arm, kept in chosen.items():
        if a.only and arm != a.only:
            continue
        m = write_sft(kept, sft_path(arm, t, r), arm=arm, round_=r, train_seed=t, note=f"played by {a.base_arm}")
        print(f"{arm:7} {m['examples']:>4} examples, {m['instances']:>4} instances, {m['output_tokens']:>7} output tokens, "
              f"sha256 {m['sha256'][:12]}")
    if a.only == "format" and a.count is not None and len(chosen["format"]) < a.count:
        print(f"warning: only {len(chosen['format'])} parsing replies for a target of {a.count}: the arms will not match in size")
    if r == 0 and a.only != "format" and len(chosen["reward"]) < MIN_REWARDED:
        nxt = max(played) + 1
        if nxt < MAX_BLOCKS_R0:
            print(f"only {len(chosen['reward'])} rewarded replies (< {MIN_REWARDED}) after {len(played)} block(s): play another "
                  f"round-0 block with --redraw {nxt}, then select again (the blocks are pooled)")
            return 3
        print(f"only {len(chosen['reward'])} rewarded replies (< {MIN_REWARDED}) after the {MAX_BLOCKS_R0} blocks allowed: the "
              "fine-tune goes on with them; write the number in docs/rl_plan.md (under 24, stop and report it)")
    return 0


def cmd_merge(a) -> int:
    """Rounds 0 and 1 of an arm added into one file: the fine-tune always starts from the base, on both rounds."""
    rows = read_sft(sft_path(a.arm, a.train_seed, 0)) + read_sft(sft_path(a.arm, a.train_seed, 1))
    out = RL / "sft" / f"t{a.train_seed}-r01-{a.arm}.jsonl"
    m = write_sft(rows, out, arm=a.arm, round_=1, train_seed=a.train_seed, note="rounds 0 and 1")
    print(f"{out.name}: {m['examples']} examples, sha256 {m['sha256'][:12]}")
    return 0


def private_first_seed() -> int:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("ORBITBENCH_TEST_FIRST_SEED_RL="):
            return int(line.split("=", 1)[1].strip().strip("\"'"))
    raise SystemExit("ORBITBENCH_TEST_FIRST_SEED_RL is not in .env: draw the private range before any training")


def cmd_evaluate(a) -> int:
    """Suite rl in condition B, k = 3, on the private range (the seed is read from .env and never printed)."""
    if a.server != "ollama" or a.sandbox != "docker":
        raise SystemExit("the evaluation is played at home, with Ollama and the Docker sandbox")
    cond = a.condition
    families, suffix = EVAL_PARTS[getattr(a, "part", "all")]       # one folder per part: a folder resumes only its own task
    folder = RL / f"eval-{a.arm}{suffix}" if cond == "B" else RL / f"eval-{a.arm}-{cond}{suffix}"
    only = ["--families", *families] if families else []
    return harness(["run", "--condition", cond, "--suite", "rl", "--first-seed", str(private_first_seed()), *only,
                    "--epochs", str(a.epochs), "--max-samples", str(samples_of(a)), "--token-limit", str(TOKEN_GUARD),
                    "--model", model_name(a.server, a.tag), "--log-dir", str(folder)])


def common(p) -> None:
    """Options of the commands that play episodes."""
    p.add_argument("--server", choices=["ollama", "vllm"], default="ollama")
    p.add_argument("--sandbox", choices=["docker", "local"], default="docker", help="local: Colab rollouts only, never results")
    p.add_argument("--max-samples", type=int, help="episodes in parallel (default 1 for Ollama, 8 for vLLM)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("phase0", help="play the 72 episodes of one bake-off candidate")
    p.add_argument("--name", required=True, help="short name of the candidate (folder phase0-<name>)")
    p.add_argument("--tag", required=True, help="Ollama tag of the model")
    common(p)
    p = sub.add_parser("bakeoff", help="the table and the choice of the rule, from the phase0-* folders")
    p.add_argument("--finetune-ok", default="", help="comma-separated candidates whose LoRA fine-tune and GGUF export worked on a T4")
    p.add_argument("--default", default="qwen3-4b")
    p.add_argument("--parallel", type=int, default=1, help="episodes in parallel during phase 0 (8 on Colab with vLLM)")
    p.add_argument("--units-per-hour", type=float, help="Colab: the rate shown for the runtime, to estimate the 9 blocks")
    p = sub.add_parser("play", help="play one block (144 distinct instances x 4 attempts)")
    p.add_argument("--arm", required=True, help="base, reward or format: names the folder")
    p.add_argument("--tag", required=True)
    p.add_argument("--train-seed", type=int, required=True)
    p.add_argument("--round", type=int, choices=[0, 1], required=True)
    p.add_argument("--redraw", type=int, choices=range(MAX_BLOCKS_R0), default=0,
                   help="round 0 only: number of the extra block (0 is the first)")
    p.add_argument("--block-n", type=int, default=BLOCK_N)
    p.add_argument("--first-seed", type=int, help="smoke runs only: play from this training seed, not the block's own range")
    common(p)
    p = sub.add_parser("select", help="write the training files of both arms for one round")
    p.add_argument("--train-seed", type=int, required=True)
    p.add_argument("--round", type=int, choices=[0, 1], required=True)
    p.add_argument("--base-arm", required=True, help="the folder name's arm that played the block")
    p.add_argument("--only", choices=["reward", "format"], help="write only this arm's file (round 1)")
    p.add_argument("--count", type=int, help="size of the format set (round 1: the examples of the reward file)")
    p = sub.add_parser("merge", help="add rounds 0 and 1 of an arm into one training file")
    p.add_argument("--train-seed", type=int, required=True)
    p.add_argument("--arm", choices=["reward", "format"], required=True)
    p = sub.add_parser("evaluate", help="suite rl on the private range")
    p.add_argument("--arm", required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--condition", choices=["A", "B", "C"], default="B")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--part", choices=list(EVAL_PARTS), default="all",
                   help="all: the 138 instances in one folder; held: the 40 held-out plans (H6) first; rest: the other 98")
    common(p)
    a = ap.parse_args(argv)
    return {"phase0": cmd_phase0, "bakeoff": cmd_bakeoff, "play": cmd_play, "select": cmd_select, "merge": cmd_merge,
            "evaluate": cmd_evaluate}[a.command](a)


if __name__ == "__main__":
    sys.exit(main())
