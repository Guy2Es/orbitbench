# orbitbench

A benchmark and RL environment for mission analysis. A model answers an astrodynamics task with a JSON
answer; the grader replays the maneuver plan in NASA GMAT through [gmat-mcp](https://github.com/Guy2Es/GMAT-MCP)
and checks the final state, so the reward comes from a simulation and not from a judge.

**Status: early development.** One family (`hohmann`) works end to end; nothing here is a result yet.
The hypotheses are recorded in [docs/hypotheses.md](docs/hypotheses.md) before any model has been run.

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

## License

MIT, see [LICENSE](LICENSE).
