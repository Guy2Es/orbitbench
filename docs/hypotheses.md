# Hypotheses and primary comparison

Recorded on 2 November 2026, before any model has been run on the benchmark. A change made after
calibration is added to "Amendments" below with its date and its reason; the text above is never edited.

## Questions, in priority order

1. **Training.** Does RL training of a small open-source model on this reward reduce the gap to the optimum
   on task families held out of training?
2. **Reliability.** How often does a model claim a verification it never did, or present a failure as a success?
3. **Value of the tool.** By how much does GMAT-MCP raise the success rate compared with Python alone (condition C minus B)?

## Primary comparison

Gap to the optimum on the held-out families, trained model against the same model before training, paired on
the same instances, with a bootstrap confidence interval (resampling families first, then instances within a
family). Questions 2 and 3 are reported separately, with their own intervals.

## Hypotheses

- **H1 (exploratory).** The tool helps mostly at levels 3 and 4 (multi-step, targeting); at levels 1 and 2 Python
  alone is enough. The split by level lacks the power of a confirmatory test, so H1 is reported per family
  without a firm conclusion.
- **H2.** Without GMAT, errors of units, frames and conventions dominate. Tested at levels 1 and 2, on
  conditions A (no tool) and B (Python only).
- **H3.** The gap between models grows with difficulty.
- **H4.** Reliability (succeeding k times out of k) is clearly lower than the success rate of a single attempt.
- **H5.** Models present a measurable share of failures as successes, including when the result signals the
  failure (a targeting run with `converged` false).
- **H6.** Training reduces the gap to the optimum on the held-out families.

## Amendments

### 2 November 2026: what v0.1 showed, and what v1.0 declares before any v1.0 run

The text above is unchanged. This entry is written before any episode of v1.0 has run.

**Observation on v0.1.** Claude Haiku 5.5 on the test seeds solved 53 of 61 instances in condition B and 56 of 61 in
condition C; the paired difference C minus B was +0.049 with a 95 % interval from -0.066 to +0.164 (it contains zero).
On a development comparison, Claude Sonnet 5.5 solved 22 of 22 episodes. In condition C, 9 of 61 episodes called a GMAT
tool; the others solved the task in Python. The v0.1 tasks (impulsive burns, point mass or J2) have closed or easily
integrated solutions, so v0.1 cannot separate the models at the top, nor test H1 and H3.

**What v1.0 adds, to make H1 and H3 testable.** Level 4 (a sun-synchronous orbit, rendezvous phasing), ill-posed
statements with well-posed twins, a measure of false claims, finite burns, condition A (no tool) at levels 1 and 2, and
k attempts per instance. The hypotheses H1 to H6 and the primary comparison stay as written above.

**Declared for the v1.0 run.**
- Models: Claude Haiku 5.5 and Claude Sonnet 5.5; Claude Opus 5.5 only on a subset of instances, if the budget allows.
- Attempts: k = 3 per instance at the provider's default temperature. If the measured cost forces a smaller k, the
  change is added here with its date.
- Budget: about 30 USD of API for the full run, with a ceiling per run and a token guard per episode (at least
  1 000 000 tokens, reported with the results, not a declared limit).
- Test seeds: a new range, drawn before the run and kept out of the repository until the results are published.
  The v0.1 test seeds are not reused.
- Success: every constraint of the reply met, as in v0.1. Reliability (H4): the share of instances solved in all k
  attempts. False claims (H5): counted by the three rules of the plan, and only after the detector has been checked by
  hand on an annotated sample.
- The v1.0 tolerances, reward, limits and prompts are frozen after the calibration pilot, in `freeze.md`, before the run.
- Results are reported by family and by level with intervals, including null and unfavourable ones. Level-wise
  intervals are exploratory.

### 8 November 2026: the lunar impact family, and which comparison it serves

**What is added.** One family outside the v1.0 catalog, `lunar_impact` (level 4): the time at which a low lunar orbit
decays to the surface, GRGM900C degree and order 50, Earth and Sun point masses, 60-day horizon, tolerance 1 day. It
exists because the answer needs data a model can neither recall nor download, so that a model with only Python cannot
close the task with a formula; `docs/lunar_baseline_rule.md` records why it was chosen (Python baseline: no impact on any
of 10 seeds, while GMAT impacts on all 10) and how its reference was checked independently of GMAT.

**Which question it serves.** Question 3 of the list above (the value of the tool, C minus B), on one task type, with
small and cheap models. It does not answer question 1 (the reinforcement-learning arms) or question 2, and it does not
replace the v1.0 run. A result on this family is reported as a result on this family only.

**Declared before the run on the test seeds.**
- Conditions: B (Python only, no network) and C (Python and the GMAT server); A is not run, the task cannot be answered
  from memory.
- Primary comparison: the paired difference C minus B in the share of instances solved, per model, with a 95 %
  bootstrap interval over the instances (resampling instances, the k attempts of an instance kept together).
- Models: gpt-oss-120b, Qwen3.7 Flash, DeepSeek V4 Flash and Gemini 2.5 Flash Lite through OpenRouter, the provider
  recorded in every exported row. Claude models are not run on it in this entry.
- Instances: the private test seeds of the family (30), attempts k = 3, message limit 60 (as frozen), token guard 1 000 000
  tokens per episode, reported with the results and not a declared limit.
- Seeds are screened by the rule of `docs/lunar_baseline_rule.md` of 8 November 2026 (the date moves by less than 0.3
  day under a 100 arcsecond change of the Moon orientation) before they enter the test set.
- Reported as they come, with the failures read one by one: no answer, invalid answer, message limit, wrong date.
  An honest `ill_posed` ("no data") in B is graded as a failure by the grader; it is counted and shown apart.
- Development results (5 seeds, one attempt, 4 models: B 0 of 20, C 11 of 20) are exploratory and are not part of the
  test results.

### 8 November 2026: the models of the v1.0 run are changed

**Change.** Claude Haiku 5.5 and Claude Sonnet 5.5 are removed from the models declared on 2 November 2026 (and Claude
Opus 5.5 with them). The v1.0 run, including the lunar line, uses four models through OpenRouter: gpt-oss-120b,
Qwen3.7 Flash, DeepSeek V4 Flash and Gemini 2.5 Flash Lite. The provider served is recorded in every exported row.

**Why.** Cost, measured by the maintainer: 27 million tokens on the Anthropic API in batch mode (half price) cost almost
5 USD, while 11 million tokens on OpenRouter cost 0.37 USD. Claude Haiku 5.5 spends many more tokens per solved instance
than the other models, so its real cost is far above its price per token. The four models are also from four different
families, which makes the comparison wider.

**What stays.** The v0.1 results with Claude Haiku 5.5 and Claude Sonnet 5.5 are kept as they are and reported as v0.1
results. The hypotheses H1 to H6, the primary comparison and the budget ceiling per run are unchanged; the budget of about
30 USD is now an upper bound, not a plan. Nothing here is a conclusion about Claude models: they are not part of the
v1.0 run.
