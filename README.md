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
python -m pytest -m "not gmat"    # no GMAT needed
python -m pytest -m gmat          # replays plans in GMAT (GMAT_INSTALL and gmat-mcp required)
```

## License

MIT, see [LICENSE](LICENSE).
