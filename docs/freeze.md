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

---

# Frozen values of v1.0 (release candidate `v1.0-rc`, 3 November 2026)

The v0.1 values above stay as they are: the 11 lines, their tolerances and the prompts of B and C are unchanged, so the
v0.1 results stay reproducible. `tests/test_freeze_v10.py` fails if one of the values below changes.

## What is frozen

- **Tolerances of every family**, v0.1 families included, level-4 families and the canaries.
  `sun_synchronous` is 0.001 deg/day on the node drift (below the secular formula's error, so the closed form does not
  pass); `finite_burn_raise` is 1 % on the final periapsis and apoapsis radii (the best circularization a long burn can
  make misses by 0.4 to 0.5 %) and 0.001 deg on the inclination.
- **Epochs of the J2 lines**: `01 Jan 2000 12:00:00.000` for `j2_drift` and `sun_synchronous`. GMAT's Earth axis departs
  from the inertial z axis by about 0.0001 deg/day of drift per year away from J2000, so the epoch stays within two years of
  it (`docs/calibration_v10.md`).
- **Reward** and **declared limits**: unchanged (60 messages, 60 s Python, 45 s GMAT wait, 300 s GMAT kill, 180 s call).
- **The three system prompts**: A (no tool), B and C. The prompts of B and C are those of v0.1, bit for bit.
- **The dataset**: 85 instances of the 14 lines and 3 trap lines, their 9 well-posed twins reported apart, and 3 canaries,
  through a hash of every field of every default instance; then the statements of the development seeds 0 to 9 of each
  line, through a second hash.
- **Reading of the reply**: when a reply holds several `<final_answer>` blocks, the last one is graded (the statement says
  "exactly one block"; across 486 episodes one reply has two, which moves no rate).

## Assumed deviations from the plan

- Finite burns are a separate level-4 family (`finite_burn_raise`), not a variant of a level-3 family.
- 85 instances instead of 80.
- The canaries (3 trivial one-formula questions) are played with every run and counted in none of its results.

## Not frozen

- **Sampling**: no temperature or other sampling setting is passed to any model (the provider's default); every exported
  row records it. Two runs are comparable only if these columns match.
- **Models, number of seeds, attempts (k) and the spending guard**: they belong to the run.
- **The false-claim rules** are validated provisionally (`docs/claims_validation.md`): `claim_unconverged` has not fired
  on any validation episode, and no human has read the transcripts.

## Seeds

- **Development seeds**: 0 to 9 of each line, used for all calibration (`docs/calibration_v10.md`).
- **Test seeds**: a new range, drawn by the maintainer on 3 November 2026 and kept out of the repository (an ignored file).
  It does not overlap the development seeds or the range of the v0.1. The release candidate was tagged before it was
  drawn; the freeze is final once the human review of the new statements is done.

## Checking

    python -m pytest tests/test_freeze.py tests/test_freeze_v10.py
