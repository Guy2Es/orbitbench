# Frozen values of v0.1

These values are fixed for the published run. `tests/test_freeze.py` fails if one of them changes; changing one is
a decision, dated here, not a side effect.

## What is frozen

- **Tolerances** of every family: the `tolerance` block of `src/orbitbench/families/templates/*.yaml`.
  Pilot evidence: no failure came from a tolerance too tight or too loose.
- **Reward**: `reward = met_fraction / (1 + max(0, gap_m_s) / 10)`, with the gap in m/s between the plan's Δv and the
  reference Δv (`grader.REWARD_SCALE_M_S`). The binary `solved` is separate and does not depend on it.
- **Declared limits**, the same for every model and condition: 60 messages per episode; 60 s per Python call;
  45 s for a gmat-mcp call to wait for its job; 300 s before a GMAT job is killed; 180 s before the client gives up
  on a call (`harness/task.py`).
- **System prompts** of conditions B and C (`harness/prompt.py`), identical for every model.
- **The statements** of the instances of the 11 lines, seeds from 0 (`harness/catalog.py`), through a hash.

## Not frozen, and why

- **Spending guard** `--token-limit`: not a declared limit. In the pilot it ended 5 episodes after 6 to 9 turns.
  For the published run it is set high enough (at least 1 000 000 tokens) that the 60-message limit ends the
  episodes, and the run reports it.
- Models, number of seeds and number of attempts: they belong to the run, not to the benchmark.

## Seeds

- **Development seeds**: 0 to 9 of each line. They were used for the pilot, the audit and the comparison. The
  default instances (61) are the seeds 0 to 5 of each line.
- **Test seeds**: a range chosen by the maintainer, kept out of the repository (an environment variable or an ignored
  file) and passed to `--first-seed` for the published run only. Their statements are not published before the results.

## Checking

    python -m pytest tests/test_freeze.py
