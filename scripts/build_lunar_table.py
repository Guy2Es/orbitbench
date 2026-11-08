# scripts/build_lunar_table.py
"""Builds src/orbitbench/families/templates/lunar_impact_table.yaml: for each seed, the first candidate of its stream
whose GMAT reference (GRGM900C degree 50, Earth and Sun) impacts within max_days, with the impact date.

Runs GMAT in the orbitbench-gmat:0.1 container (no network) with this file as the worker. Usage:
    python scripts/build_lunar_table.py --seeds 0-14 [--containers 3]
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # "/" inside the container, where the file is /worker.py
FAMILIES = ROOT / "src" / "orbitbench" / "families"
TABLE = FAMILIES / "templates" / "lunar_impact_table.yaml"
IMAGE = "orbitbench-gmat:0.1"
SETTINGS = {"integrator": "PrinceDormand78", "accuracy": 1e-12, "max_step_s": 300}   # setting S1 of lunar_baseline_rule.md


def worker(seeds, out_path):
    """Inside the container: /src is the repository's src folder, read-only."""
    sys.path.insert(0, "/opt/app")
    from core.runner.run import run_mission
    draw_spec = importlib.util.spec_from_file_location("lunar_draw", "/src/orbitbench/families/lunar_draw.py")
    draw = importlib.util.module_from_spec(draw_spec)
    draw_spec.loader.exec_module(draw)
    tpl = json.loads(Path("/work/template.json").read_text(encoding="utf-8"))   # PyYAML is not in the container
    skip = json.loads(Path("/work/skip.json").read_text(encoding="utf-8"))   # seed -> candidates already used or screened out
    for seed in seeds:
        rejected = 0
        for idx, p in enumerate(draw.candidates(seed, tpl["ranges"], tpl["epoch_start"], tpl["epoch_days"])):
            if idx < skip.get(str(seed), 0):
                rejected += 1
                continue
            if rejected >= tpl["max_candidates"]:
                raise RuntimeError(f"no impacting candidate in {rejected} tries for seed {seed}")
            mission = {
                "spec_version": "1", "name": f"lunar{seed}", "central_body": "Luna", "epoch": p["epoch"],
                "spacecraft": [{"name": "S", "dry_mass_kg": 500, "state": {"type": "keplerian",
                                **{k: p[k] for k in draw.ELEMENTS}}}],
                "force_models": [{"name": "FM", "gravity": tpl["gravity"], "third_bodies": ["Earth", "Sun"]}],
                "propagators": [{"name": "P", "force_model": "FM", "initial_step_s": 30, "min_step_s": 0, **SETTINGS}],
                "sequence": [{"type": "propagate", "propagator": "P", "spacecraft": ["S"], "max_days": tpl["max_days"],
                              "stop": {"type": "parameter", "quantity": "periapsis_radius_km",
                                       "value": draw.MOON_RADIUS_KM}}],
                "outputs": [{"type": "report", "name": "R", "spacecraft": "S",
                             "fields": ["elapsed_days", "periapsis_radius_km"]}]}
            run = run_mission(mission, tempfile.mkdtemp(prefix="job_", dir="/tmp/jobs"), backend="local", timeout_s=900)
            if not run.results:
                raise RuntimeError(f"GMAT failed for seed {seed}: {run.run.reason}")
            cols = run.results.reports["R"].columns
            if min(cols["periapsis_radius_km"]) <= draw.MOON_RADIUS_KM + 1e-6:
                row = {"params": p, "impact_days": round(float(cols["elapsed_days"][-1]), 4), "rejected": rejected}
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"seed": seed, **row}) + "\n")
                break
            rejected += 1


def parse_seeds(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="e.g. 0-14 or 0,3,5-7")
    ap.add_argument("--containers", type=int, default=3)
    ap.add_argument("--table", default=str(TABLE), help="table file to read and write (a private file for the test seeds)")
    ap.add_argument("--redo", default="", help="seeds whose row is replaced by the next impacting candidate of their stream")
    args = ap.parse_args()
    seeds = parse_seeds(args.seeds)
    table = Path(args.table)
    existing = yaml.safe_load(table.read_text(encoding="utf-8")) if table.exists() else {}
    existing = dict(existing or {})
    skip = {}
    for s in parse_seeds(args.redo) if args.redo else []:
        skip[str(s)] = existing.pop(s)["rejected"] + 1   # the old kept candidate is index `rejected`
    todo = [s for s in seeds if s not in existing]
    work = Path(tempfile.mkdtemp(prefix="lunar_build_"))
    template = yaml.safe_load((FAMILIES / "templates" / "lunar_impact.yaml").read_text(encoding="utf-8"))
    (work / "template.json").write_text(json.dumps(template), encoding="utf-8")
    (work / "skip.json").write_text(json.dumps(skip), encoding="utf-8")
    procs = []
    for k in range(min(args.containers, len(todo))):
        mine = todo[k::args.containers]
        cmd = ["docker", "run", "--rm", "--network", "none", "-v", f"{ROOT / 'src'}:/src:ro", "-v", f"{work}:/work",
               "-v", f"{Path(__file__).resolve()}:/worker.py:ro", "--entrypoint", "/opt/venv/bin/python", IMAGE,
               "/worker.py", "--worker", ",".join(map(str, mine)), f"/work/out{k}.jsonl"]
        procs.append(subprocess.Popen(cmd))
    t0 = time.time()
    codes = [p.wait() for p in procs]
    rows = dict(existing)
    for f in work.glob("out*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            rows[r.pop("seed")] = r
    table.parent.mkdir(parents=True, exist_ok=True)
    table.write_text("# Built by scripts/build_lunar_table.py (GMAT, GRGM900C degree 50). Do not edit by hand.\n" +
                     yaml.safe_dump({int(k): rows[k] for k in sorted(rows)}, sort_keys=True), encoding="utf-8")
    print(f"{len(rows)} seeds in the table, {time.time() - t0:.0f} s, container exit codes {codes}")
    return 0 if all(c == 0 for c in codes) else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker([int(x) for x in sys.argv[2].split(",")], sys.argv[3])
    else:
        sys.exit(main())
