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

## Result of the lunar test run (9 November 2026): DeepSeek V4 Flash not evaluable

Protocol, tools and prompts are unchanged. The run (`scripts/run_lunar_test.py --ceiling 8.0`) completed gpt-oss-120b,
Gemini 2.5 Flash Lite and Qwen3.7 Flash in B and C (6 steps, 4.07 USD of the 8 USD ceiling), then stopped at DeepSeek V4 Flash
in C.

- **What failed.** OpenRouter answered `404 - No endpoints found that support image input`. In episode
  `lunar_impact:values:636226495` the model called `plot_trajectory_3d`, a tool of the gmat-mcp server that returns an image;
  the image went back into the conversation, and DeepInfra, the pinned provider, serves DeepSeek V4 Flash as text only.
  The other errors of that run (seeds 494, 496, 497) are cancellations that followed. 9 of 90 samples were logged.
- **Decision (maintainer).** The tools of condition C are not modified, and no image is removed or replaced, so every
  model keeps the same tools and the same inputs. DeepSeek V4 Flash is set aside as **not evaluable**: the reason is not
  that the model fails, but that its results cannot be used. With the pinned provider it cannot receive the image a tool may
  return, so the episodes that reach such a tool end in an error, not in an answer, and the cell would not measure the
  same thing as the others. It has no score in B or in C. DeepSeek V4 Flash B was not run. The 13 episodes written in
  `runs/lunar-test-dsflash-C/episodes.jsonl` are kept for audit and counted in no result. The rule above (an `error` episode is
  rerun) was not applied to them: a rerun hits the same refusal.
- **Do not relaunch the command as is**: it would replay `dsflash-C` and fail the same way.
- **Qwen3.7 Flash** called one plotting tool in the whole run (`plot_orbital_elements`, seed 636226501, epoch 3); its endpoint
  accepts images and the episode ran normally. gpt-oss-120b and Gemini 2.5 Flash Lite called none.
- **Measured success rate over 90 episodes** (3 epochs x 30 seeds): gpt-oss-120b B 0 % and C 58 %; Gemini 2.5 Flash Lite B 0 %
  and C 43 %; Qwen3.7 Flash B 0 % and C 59 % (`runs/lunar_test_run.log`).
- **v1.0**: condition C of v1.0 has the same exposure for DeepSeek V4 Flash through DeepInfra, because the plotting tools are
  the same. It is set aside there as well, for the same reason (next entry).

## Run of v1.0 on the test seeds (9 November 2026): settings declared before the run

Nothing frozen above changes. No episode of v1.0 had run on the test seeds when this entry was written.

- **Models**: gpt-oss-120b (provider Crusoe, pinned, no fallback), Gemini 2.5 Flash Lite and Qwen3.7 Flash, through
  OpenRouter, with `--deny-data-collection`. **DeepSeek V4 Flash is set aside**, for the reason of the entry above (its
  results cannot be used, which is not a judgment on the model). It may be added later with the same protocol, in the order
  A, B, C, and reported as it comes; nothing in this run depends on it.
- **Suites**: `v10` with 5 seeds per line (79 instances: the three trap lines have 3 seeds in the catalog, which is not
  changed), then `twins` (9) and `canary` (3). Condition A plays the instances of levels 1 and 2 (34 + 9 + 3); B and C play
  all of them. One attempt per instance (k = 1), message limit 60, token guard 1 000 000, the provider's default sampling.
- **Test seeds**: the first seed was `ORBITBENCH_TEST_FIRST_SEED_V10` in `.env`, ignored by git, and was not written here until the
  results were published; it is now in [test_seeds.md](test_seeds.md) (9 November 2026).
  Checked on 9 November 2026: six digits, so below 1 000 000 (the training seeds of `docs/rl_plan.md` start there), no overlap
  with the development seeds 0 to 9 and none with the seeds of the v0.1 test run. The same first seed is used by `v10`, `twins`
  and `canary`.
- **Run**: `scripts/run_v10_test.py --ceiling <USD>`, one step per (model, condition, suite) from the cheapest model up, a step
  not started if it could cross the ceiling, resumable. Upper bound of the whole plan: 3.33 USD (the measured upper bound per
  instance times 1.25; condition A is an assumption, not measured). The ceiling is set at launch.
- **Reported**: kinds of failure as above; an `error` episode is rerun and the reruns are counted; the failures are read one by
  one; the results are per family and per level with intervals, level-wise ones being exploratory.
- **Not tested**: H4 (reliability) needs at least two attempts, so it is not tested by this run. H5 uses the false-claim rules,
  validated provisionally (`docs/claims_validation.md`); `claim_unconverged` has not been tested on an episode that did not
  converge.
- **Human reviews, recorded on 9 November 2026 on the maintainer's confirmation** (both were done before this date and not
  written down then): the review of the new statements of v1.0, which makes the freeze final, and the author's reading of the
  disputed episodes of the false-claim validation. For `r17` (two answer blocks), see the decision in
  `docs/claims_validation.md`.

## Run of v1.0 on the test seeds (9 November 2026): reading of the failures and decisions

Nothing frozen above changes: the protocol, the catalog and the strict parser stay as they were. The run finished with 684
episodes (576 of `v10`, 81 twins, 27 canaries), none in `error`, for 3.17 USD. The 358 unsolved episodes of `v10` were read one
by one. The decisions below were taken by the maintainer on 9 November 2026.

- **Five episodes of Gemini 2.5 Flash Lite in condition B are set aside**: the provider answered `UNAVAILABLE` (an
  infrastructure failure, not an answer of the model). They are 3 `finite_burn_raise` and 2 `rendezvous_phasing` instances.
  They are not rerun (rule: no retry) and are counted in no result: the cell has 74 episodes, not 79, and the files
  `episodes.jsonl` still hold them, so a count from the files must remove them. The other 22 episodes of Gemini that ended with
  `MALFORMED_FUNCTION_CALL` (13 in B, 9 in C) stay counted: the model produced the malformed call.
- **The parser stays strict** (`<final_answer>` block, plain JSON). A lenient re-grading (code fence accepted, extra closing
  brace accepted, unclosed or missing tag accepted) turns only about 10 of the 205 `invalid_format` episodes into `solved`
  (about 50 plans could not be re-graded without GMAT), so the parser is not what drives the results. It is not a second
  table of results.
- **`tle_state` stays in condition A and is not removed**: removing it after the run would change the catalog the run was
  declared on. It is reported as is, with the per-line table. In A it was solved 0 times in 15 (5 per model): gpt-oss-120b and
  Qwen3.7 Flash mostly answer `ill_posed` ("SGP4 cannot be done by hand"), which the grader marks `wrong_status` because the
  task is well posed. The A figures are also given without this line (29 instances per model) next to the full ones, as an
  exploratory reading. This is a limit of A, not evidence on the models' knowledge.
- **Failures that are not about orbital mechanics, to keep in mind when reading A against B and C**:
  - gpt-oss-120b in A: 13 of 34 replies have an empty content after the reasoning (`stop`, no text). There is nothing to
    grade. It lowers its A score and so the B−A and C−A gaps for this model.
  - Gemini 2.5 Flash Lite: besides the 27 provider errors above, 12 replies in C end with an empty `STOP`, and 15 in A have
    the JSON without the `<final_answer>` tags or inside a code fence.
  - Qwen3.7 Flash: about 45 episodes in B and C reach the 60-message limit or the token guard without answering (up to 29
    Python calls, 500 000 to 1 million tokens); in C it repeats `reset_session` and `create_spacecraft` without converging.
    Twelve answers have one closing brace too many (`}}}`).
  - gpt-oss-120b: a stray quote before `</final_answer>` in 4 episodes, and some blocks never closed.
- **Failures on the content**: 63 of 81 trap episodes are `missed_trap` (the models answer `solved`; 4 episodes of Gemini on
  `trap_isp` mention the assumed Isp in `claims` and still give a number). In `j2_drift` several models, in A, B and C, show
  the same error of about 0.3 deg on the argument of periapsis: they use the secular formula, not a propagation. In `sun_synchronous`
  the analytic inclination misses the drift tolerance (one sign error). Three gpt-oss episodes of `state_at_date` have exact
  positions and wrong velocities (a wrong angle in the perifocal velocity, never checked).
- **Claims**: one `claim_unconverged` episode in 684 (Qwen3.7 Flash, C, `circularize_plan`, graded `solved`, final eccentricity
  about 4e-8). It does not validate the rule: it is one occurrence. `claim_unchecked` is nearly absent outside A.
  `claim_contradicted` is highest for gpt-oss-120b in B and C (13 and 15 episodes, twins and canaries included).
- **Twins** (9 per cell, solved): gpt-oss A 5, B 7, C 9; Gemini A 2, B 8, C 8; Qwen 9 in the three. C−B is not
  distinguishable from zero for any model. **Canaries** (3 per cell, counted in no result): gpt-oss and Qwen 3/3 in B and C,
  Gemini 2/3 everywhere; they flag no anomaly.
- **Solved over `v10`** (before removing the 5 episodes above): gpt-oss A 4/34, B 42/79, C 51/79; Gemini A 0/34, B 17/79
  (17/74 without the 5), C 17/79; Qwen A 11/34, B 47/79, C 29/79. H4 is not tested and DeepSeek V4 Flash stays set aside.

## DeepSeek V4 Flash dropped (9 November 2026)

On the maintainer's decision, DeepSeek V4 Flash leaves the benchmark: it is no longer "set aside, may be added later" but
dropped, for the lunar line and for v1.0. It has no score anywhere. Reason unchanged (the pinned provider cannot receive the
image a gmat-mcp plotting tool may return, so its condition C episodes end in an error); this is not a judgment on the
model. Its entry is removed from `scripts/run_lunar_test.py` so that a relaunch cannot replay it; the 13 partial episodes in
`runs/lunar-test-dsflash-C/` and the cost-sample runs `runs/cost-v10-dsflash-*` stay for audit only and are counted in no
result. The earlier entries are not edited: they record what was decided at the time.

## Lunar test seeds published (10 November 2026)

The article is finished, so the 30 lunar test seeds are published in `docs/test_seeds.md` and the range is **spent**: it
must not be reused to evaluate a model, to train one or to tune anything. Nothing frozen changes. The earlier entries that
say the range is private record what was true at the time.

## Reward not reported (10 November 2026)

The reward frozen above (`reward = met_fraction / (1 + max(0, gap_m_s) / 10)`) is still computed by the grader and written in
the exports, and the code is unchanged, but no result of the report uses it: the only success measure reported is the binary
`solved`, which never depended on it. The tables of the report have no reward column. This is a deviation from what was
declared at the freeze, dated here; the earlier entries are not edited.

## Server version of the published runs (10 November 2026)

Every published episode (v0.1, v1.0, lunar) ran with the gmat-mcp server of `docker/app/`, which is identical, file by file,
to the commit `d161333` of `https://github.com/Guy2Es/GMAT-MCP` (2 November 2026), before version 0.2.0. Version 0.2.0
(commit `63d93eb`) changes the defaults that the lunar failures exposed (60-day bound, explicit lunar gravity field, a long
call returned as a normal `running` answer). The published runs were not replayed with it, so their numbers belong to
`d161333`.
