# scripts/rl_draw_seed.py
"""Draw the private test range of the RL study (docs/rl_plan.md), once, before any training run.

  python scripts/rl_draw_seed.py                # draws, writes .env, prints the commitment
  python scripts/rl_draw_seed.py --commitment   # prints the commitment of the range already drawn

The first seed is written in .env as ORBITBENCH_TEST_FIRST_SEED_RL and is never printed. What is printed is a commitment: the
SHA-256 of "orbitbench-rl:<first seed>:<salt>", the salt being a random string kept in .env as well. The commitment goes in
docs/rl_plan.md before any training. When the results are published, the seed and the salt are published with them, and anyone
can check that the range was fixed first. The salt is needed because a seed below one million could be found by trying them all.

The range stays below the training seeds (1,000,000 and above), away from the development seeds (0 to 9) and from the
published, spent ranges of docs/test_seeds.md. The script refuses to draw twice."""
import argparse
import hashlib
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY, SALT_KEY = "ORBITBENCH_TEST_FIRST_SEED_RL", "ORBITBENCH_TEST_SEED_RL_SALT"
LOW, HIGH = 10_000, 990_000      # the first seed is drawn in [LOW, HIGH); a line of the suite uses at most 20 seeds from it
SPENT = (714_002, 893_483)       # first seeds of v0.1 and v1.0 (docs/test_seeds.md); the lunar range is far above HIGH
MARGIN = 1_000                   # no first seed within this distance of a spent one


def allowed(seed: int) -> bool:
    return LOW <= seed < HIGH and all(abs(seed - s) >= MARGIN for s in SPENT)


def draw(randbelow=secrets.randbelow) -> int:
    """A first seed, uniform over the allowed values."""
    while True:
        seed = LOW + randbelow(HIGH - LOW)
        if allowed(seed):
            return seed


def commitment(seed: int, salt: str) -> str:
    return hashlib.sha256(f"orbitbench-rl:{seed}:{salt}".encode("utf-8")).hexdigest()


def read_env(text: str) -> dict:
    pairs = (line.split("=", 1) for line in text.splitlines() if "=" in line and not line.lstrip().startswith("#"))
    return {k.strip(): v.strip().strip("\"'") for k, v in pairs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commitment", action="store_true", help="print the commitment of the range already in .env")
    a = ap.parse_args(argv)
    env = ROOT / ".env"
    text = env.read_text(encoding="utf-8") if env.exists() else ""
    values = read_env(text)
    if a.commitment:
        if KEY not in values or SALT_KEY not in values:
            raise SystemExit(f"{KEY} and {SALT_KEY} are not both in .env: draw the range first")
        print(commitment(int(values[KEY]), values[SALT_KEY]))
        return 0
    if KEY in values:
        raise SystemExit(f"{KEY} is already in .env: the range is drawn once. --commitment prints its commitment.")
    seed, salt = draw(), secrets.token_hex(16)
    with open(env, "a", encoding="utf-8", newline="\n") as f:
        f.write(("" if not text or text.endswith("\n") else "\n") + f"{KEY}={seed}\n{SALT_KEY}={salt}\n")
    print(f"{KEY} is written in .env and is not shown.")
    print(f"commitment, SHA-256 of 'orbitbench-rl:<first seed>:<salt>': {commitment(seed, salt)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
