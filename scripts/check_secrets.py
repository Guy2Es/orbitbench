# scripts/check_secrets.py
"""Scan the git-tracked (or --staged) files for credential patterns. Exit 1 on a hit; never prints the matched value."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = {"api key": r"sk-ant-[A-Za-z0-9_\-]{8,}", "accessToken": r"accessToken", "refreshToken": r"refreshToken",
            "sessionKey": r"sessionKey", "credentials": r"credentials"}
# Files that legitimately name the patterns (this scanner and the git hygiene files).
ALLOW = {"scripts/check_secrets.py", "README.md", ".gitignore", ".env.example", ".pre-commit-config.yaml"}
# Allowed files still must not contain a real-looking key: only fake ones (with FAKE) pass.
REAL_KEY = re.compile(r"sk-ant-(?![A-Za-z0-9_\-]*FAKE)[A-Za-z0-9_\-]{8,}")


def files(staged: bool) -> list[str]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"] if staged else ["git", "ls-files"]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()


def scan(path: str) -> list[str]:
    p = Path(path)
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8", errors="ignore")
    if path in ALLOW:
        return ["real-looking api key"] if REAL_KEY.search(text) else []
    return [name for name, pat in PATTERNS.items() if re.search(pat, text)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true")
    args = ap.parse_args()
    bad = {f: hits for f in files(args.staged) if (hits := scan(f))}
    for f, hits in bad.items():
        print(f"{f}: {', '.join(hits)}")
    print(f"check_secrets: {'FAILED' if bad else 'clean'} ({len(bad)} file(s) flagged)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
