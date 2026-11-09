# scripts/mark_unavailable.py
"""Lists the episodes of the v1.0 test run that ended on a provider failure (`UNAVAILABLE`) and writes them to
private/excluded_episodes.json ({run folder: [episode ids]}), which `analyze --exclude` reads. Ids contain the test seeds:
the file is private and nothing is printed but counts. Decision of 9 November 2026 (docs/freeze.md)."""
import glob
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from inspect_ai.log import read_eval_log  # noqa: E402

out: dict[str, list[str]] = {}
for d in sorted(glob.glob(str(ROOT / "runs" / "v10-test-*"))):
    for f in glob.glob(d + "/*.eval"):
        for s in read_eval_log(f).samples or []:
            events = [e for e in s.events if e.event == "model"]
            resp = ((events[-1].call.response if events and events[-1].call else None) or {})
            native = ((resp.get("choices") or [{}])[0]).get("native_finish_reason")
            if native == "UNAVAILABLE":
                out.setdefault(Path(d).name, []).append(s.id)
(ROOT / "private").mkdir(exist_ok=True)
(ROOT / "private" / "excluded_episodes.json").write_text(json.dumps(out), encoding="utf-8")
print({k: len(v) for k, v in out.items()}, "total", sum(map(len, out.values())))
