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

# Amendment of 8 November 2026: the lunar impact family (outside the v1.0 freeze)

Nothing frozen above changes. `lunar_impact` is a separate line (`--suite lunar`), under `docs/lunar_baseline_rule.md`
and the amendment of `docs/hypotheses.md` of the same date.

- **Frozen for this line**: its tolerance (1 day on the impact date), its statement (which names DE405, the Earth and Sun
  GM values and the MOON_PA frame), the horizon (60 days), the ranges of the draw (periapsis altitude 20 to 45 km,
  eccentricity 0.003 to 0.008, inclination 45 to 85 deg), and the reference setting (GMAT PrinceDormand78, accuracy 1e-12,
  step at most 300 s). `tests/test_freeze_v10.py` excludes the line from the scan of v1.0 tolerances (`POST_FREEZE`) and
  `tests/test_lunar_impact.py` checks the line itself.
- **Seeds**: development seeds 0 to 14 (table in the repository); test seeds, 30 of them, drawn on 8 November 2026 as
  one range of consecutive integers by a random draw, and kept in `private/lunar_impact_table.yaml`, which git ignores.
  They do not overlap the development seeds. `ORBITBENCH_LUNAR_PRIVATE_TABLE` names another file.
- **Screening**: a candidate is kept only if its GMAT impact exists within 60 days and the independent propagator moves
  its date by less than 0.3 day under both signs of the orientation offset (`scripts/validate_lunar_reference.py`).
- **Checking**: `python -m pytest tests/test_lunar_impact.py`.

## v1.1 (8 November 2026): v1.0 unchanged, plus the lunar line as a separate stratum

v1.1 is v1.0 with one more line, `lunar_impact`, reported apart from the 14 lines of v1.0 and the traps and canaries. Every
value of v1.0 above is unchanged, and the v1.0 dataset hash is not recomputed: the lunar line is not part of it.
`tests/test_freeze_lunar.py` freezes the new line and replaces the earlier exclusion (`POST_FREEZE`) with a check of its
own values:

- the template: tolerance 1 day, horizon 60 days, field GRGM900C degree and order 50, epoch range, ranges of the draw;
- the reference setting of `scripts/build_lunar_table.py` (PrinceDormand78, accuracy 1e-12, steps of at most 300 s);
- the statements of development seeds 0 to 14 (SHA-256 `adfd5780...63bb1f`) and the development table, with its impact dates
  (SHA-256 `bc8361bd...18b16f`);
- the sizes of the suites: `--suite lunar` is the 15 development seeds, `--suite lunar_test` is the 30 test seeds, played with
  `--first-seed` set to the first of them (kept in `private/lunar_test_range.txt`, ignored by git).

**Review done (8 November 2026).** The maintainer read the lunar statement and validated it unchanged, so the hash above stands.
If its text is changed later, the hash is updated here, with the date, before any run on the test seeds.

**Run settings for the test seeds, declared before the run.**
- Condition B and C only, models gpt-oss-120b, Qwen3.7 Flash, DeepSeek V4 Flash and Gemini 2.5 Flash Lite through OpenRouter.
- `--deny-data-collection`: only providers that do not store prompts, because the 30 test statements are sent to the
  providers. A model with no such provider would fail with an error and be reported, not silently replaced.
- Provider pinned with no fallback for the two models that were served by five providers in the pilot (gpt-oss-120b: Crusoe;
  DeepSeek V4 Flash: DeepInfra, the most used of its five in the pilot). Qwen3.7 Flash (Alibaba) and Gemini 2.5 Flash Lite
  (Google AI Studio) had one provider each. Every exported row records `provider_requested` and `providers` (the provider
  that served each call).
- Message limit 60, token guard 1 000 000 per episode, k = 3 (`--epochs 3`), the provider's default sampling.
- An episode that ends in an `error` (a provider refusing or failing) is rerun, and the reruns are counted and reported; it
  is not scored as a failed answer.
- Failures are reported in four kinds (refused, wrong answer, no usable answer, plan or run failed), a refusal being an honest
  `ill_posed` that the grader scores as a failure.
