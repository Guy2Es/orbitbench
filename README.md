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

Each row also records what the episode was played with: the temperature (`provider_default` when none is set, which
is the case for every run so far: no sampling setting is passed to any model), `top_p`, `max_tokens`,
`reasoning_effort`, whether the batch API was used, the message and token limits, the number of epochs and the
Inspect version. Two runs are comparable only if these columns match.

## Results so far

Claude Haiku 5.5 and Claude Sonnet 5.5, one attempt per instance, 61 instances per condition, on test seeds that
were not used to build or tune anything. Intervals are 95 % Wilson intervals; the difference is paired and uses a
hierarchical bootstrap (families, then instances).

| Condition | Solved | Interval | Mean reward |
|---|---|---|---|
| B, Python alone | 53 / 61 | 76 % to 93 % | 0.89 |
| C, Python and gmat-mcp | 56 / 61 | 82 % to 96 % | 0.91 |

Claude Sonnet 5.5:

| Condition | Solved | Interval | Mean reward |
|---|---|---|---|
| B, Python alone | 61 / 61 | 94 % to 100 % | 1.00 |
| C, Python and gmat-mcp | 59 / 61 | 89 % to 99 % | 0.97 |

C minus B, Haiku: +0.049 solved (interval -0.089 to +0.210). Sonnet: -0.033 (interval -0.111 to 0.000). The
intervals contain zero or touch it: this run does not show that gmat-mcp helps or hurts. v0.1 is saturated for Sonnet. In C, 9 of 61 Haiku episodes called a GMAT tool; the
others solved the task in Python, because the v0.1 tasks (impulsive burns, point mass or J2) have closed or easily
integrated solutions. Tasks that need the simulation are planned for v1.0.

The 15 failures (13 Haiku, 2 Sonnet) were read one by one ([docs/test_audit.md](docs/test_audit.md)): all are mistakes of the model, none
a defect of the benchmark. Two C episodes ended on a spending guard of 1 000 000 tokens, not on a declared limit.

Reproduce the table from the run folders: `python -m orbitbench.harness analyze runs/b runs/c`.

## License

MIT, see [LICENSE](LICENSE).
