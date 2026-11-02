# orbitbench

A benchmark and RL environment for mission analysis. A model answers an astrodynamics task with a JSON
answer; the grader replays the maneuver plan in NASA GMAT through [gmat-mcp](https://github.com/Guy2Es/GMAT-MCP)
and checks the final state, so the reward comes from a simulation and not from a judge.

**Status: v0.1, in progress.** Ten task families (11 lines, 61 instances), impulsive burns only, two conditions:
B (Python alone) and C (Python plus gmat-mcp). The tolerances, reward, limits and prompts are frozen
([docs/freeze.md](docs/freeze.md)). The hypotheses were recorded in [docs/hypotheses.md](docs/hypotheses.md) before
any model was run.

## Requirements

- Python 3.10 or later.
- GMAT R2026a with its Python API, and `GMAT_INSTALL` pointing at its folder (only the replay needs it).
- A checkout of gmat-mcp. `GMAT_MCP_PATH` points at it; by default orbitbench looks for a sibling `GMAT-MCP` folder.

## Tests

```
pip install -e ".[dev]"
python -m pytest -m "not gmat and not docker"   # no GMAT, no Docker needed
python -m pytest -m gmat          # replays plans in GMAT (GMAT_INSTALL and gmat-mcp required)
python -m pytest -m docker        # the sandboxes of conditions B and C (images below required)
```

## Running a model

The harness is an [Inspect](https://inspect.aisi.org.uk) task. Condition B gives the model a Python interpreter
(numpy, scipy, sgp4) in a sandbox without network. Condition C adds the gmat-mcp server in a second sandbox;
the interpreter cannot reach GMAT except through that server. The reply is graded on the host by replay in GMAT.

```
pip install -e ".[harness]"
docker build -f docker/python.Dockerfile -t orbitbench-python:0.1 docker
sh docker/build_gmat.sh           # needs the gmat-worker image of gmat-mcp (docker/worker/Dockerfile)
python -m orbitbench.harness run --condition C --model anthropic/claude-haiku-5-5 --log-dir runs/c-haiku
```

Relaunching the same command resumes an interrupted run. Each run writes Inspect logs (full transcripts) and
`episodes.jsonl`, one row per episode. The limits (messages, tool and GMAT timeouts) are constants in
`orbitbench/harness/task.py`, the same for every model.

## Results so far

Claude Haiku 5.5, one attempt per instance, 61 instances per condition, on test seeds that were not used to
build or tune anything. Intervals are 95 % Wilson intervals; the difference is paired by instance (bootstrap).

| Condition | Solved | Interval | Mean reward |
|---|---|---|---|
| B, Python alone | 53 / 61 | 76 % to 93 % | 0.89 |
| C, Python and gmat-mcp | 56 / 61 | 82 % to 96 % | 0.91 |

C minus B: +0.049 solved (interval -0.066 to +0.164), +0.020 reward (interval -0.085 to +0.129). The interval
contains zero: this run does not show that gmat-mcp helps or hurts. In C, 9 of 61 episodes called a GMAT tool; the
others solved the task in Python, because the v0.1 tasks (impulsive burns, point mass or J2) have closed or easily
integrated solutions. Tasks that need the simulation are planned for v1.0.

The 13 failures were read one by one ([docs/test_audit.md](docs/test_audit.md)): all are mistakes of the model, none
a defect of the benchmark. Two C episodes ended on a spending guard of 1 000 000 tokens, not on a declared limit.

A second model (Claude Sonnet 5.5) is not in these results yet: the API usage limit was reached before its runs.
A first comparison on 11 development instances (not the test seeds) solved 22 of 22 episodes for Sonnet and 20 of 22
for Haiku.

Reproduce the table from the run folders: `python -m orbitbench.harness analyze runs/b runs/c`.

## License

MIT, see [LICENSE](LICENSE).
