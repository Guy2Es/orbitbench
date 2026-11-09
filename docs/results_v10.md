# Results of v1.0 on the test seeds (9 November 2026)

Three models through OpenRouter (gpt-oss-120b on Crusoe, Gemini 2.5 Flash Lite on Google AI Studio, Qwen3.7 Flash on Alibaba),
conditions A, B and C, one attempt per instance (k = 1), 79 instances of `v10` (A: 34, levels 1 and 2). Protocol, exclusions and
the reading of the failures: `docs/freeze.md`. The 5 Gemini B episodes that ended on a provider failure are counted in no
result (74 instead of 79). Twins and canaries are reported apart, in `docs/freeze.md`.

Reproduce (the exclusion file is private, it holds episode ids that contain the test seeds):
`python scripts/mark_unavailable.py` then
`python -m orbitbench.harness analyze runs/v10-test-*-v10 --exclude private/excluded_episodes.json --by-level`.
Intervals: 95 % Wilson for a rate, 95 % paired hierarchical bootstrap (families, then instances) for a difference. With k = 1
and 79 instances they are wide; the tables by level and by line are exploratory.

## Success rate (every constraint met)

| Model | A (34) | B | C |
|---|---|---|---|
| gpt-oss-120b | 4/34 (5 to 27 %) | 42/79 (42 to 64 %) | 51/79 (54 to 74 %) |
| Gemini 2.5 Flash Lite | 0/34 (0 to 10 %) | 17/74 (15 to 34 %) | 17/79 (14 to 32 %) |
| Qwen3.7 Flash | 11/34 (19 to 49 %) | 47/79 (48 to 70 %) | 29/79 (27 to 48 %) |

## Question 3: C minus B, same instances

| Model | pairs | C − B | interval |
|---|---|---|---|
| gpt-oss-120b | 79 | +0.114 | −0.061 to +0.311 |
| Gemini 2.5 Flash Lite | 74 | +0.000 | −0.175 to +0.181 |
| Qwen3.7 Flash | 79 | −0.228 | −0.419 to −0.038 |

By level (exploratory), C − B: gpt-oss L1 −0.20, L2 +0.21, L3 0.00, L4 +0.40 (−0.07 to +0.80); Gemini L1 −0.10, L2 +0.21
(0.00 to +0.46), L3 −0.10, L4 −0.10; Qwen L1 −0.30, L2 +0.04, L3 −0.40 (−0.67 to −0.10), L4 −0.27. The negative Qwen result comes
from episodes that never answer: in C, 33 of 79 end on the message or token limit (16 of 79 in B), after up to 30 tool calls and
500 000 to 1 million tokens, with `reset_session` and `create_spacecraft` repeated without converging.

## Reading of the hypotheses

- **H1 (the tool helps at levels 3 and 4).** Not supported as a general result. Only gpt-oss-120b moves the expected way at
  level 4 (+0.40, interval containing zero); Gemini and Qwen do not, and no model gains at level 3. At level 2 Gemini and
  gpt-oss gain about +0.21. Per line (below) the picture is mixed. Exploratory, no firm conclusion.
- **H2 (without GMAT, errors of units, frames and conventions dominate; A against B, levels 1 and 2).** Not settled. B − A is
  +0.38 for gpt-oss (+0.13 to +0.61), +0.27 for Gemini (0.00 to +0.59) and +0.21 for Qwen (−0.11 to +0.53). But the outcome
  labels do not say "unit" or "frame" errors, and A is dominated by failures that are not about orbital mechanics:
  gpt-oss 15/34 and Gemini 28/34 give no usable answer (empty content, missing tags), 4 of gpt-oss's and 4 of Qwen's are
  honest refusals on `tle_state`. H2 as written cannot be read from these labels.
- **H3 (the gap between models grows with difficulty).** Weakly consistent, confounded. In B all three models are close at
  level 1 (9/10 each); at level 3 they are 7/30 (Gemini), 22/30 (gpt-oss) and 23/30 (Qwen), at level 4 1/10, 3/15 and 6/15. The gap
  opens at level 2 already and is mostly Gemini's output failures (provider errors, empty replies), not a gap of reasoning.
- **H4 (reliability).** Not tested: k = 1.
- **H5 (failures presented as successes).** Measurable. Of the episodes that claim `verified: true`, the answer is contradicted
  by the grader in: Gemini B 13 of 28, C 6 of 21; gpt-oss B 13 of 33, C 15 of 59; Qwen B 2 of 28, C 4 of 32. `claim_unchecked`
  fires only in A, where there is no tool (Gemini 4, gpt-oss 1, Qwen 7), and once in C. `claim_unconverged` fires once in 576
  (Qwen, C, graded `solved`). The author read it (docs/claims_validation.md, 9 November 2026): the model abandoned a failed
  targeting call, applied the burn by hand and replayed it to a converged state, so the flag is a false positive; one case
  supports no rate, and the rule is not changed for v1.0.
- **H6 and question 1 (training).** Not served by this run.

## The contradicted claims of gpt-oss-120b, read one by one

28 episodes (B 13, C 15): 16 `missed_trap`, 9 `constraints_violated`, 3 `values_mismatch`. In all of them, `claims.method`
describes a computation ("analytical Hohmann transfer", "J2 secular rates", "nodal regression formula") and says nothing
about a check: the model writes `verified: true` for "I computed it". In the 9 plan failures of C, GMAT was not used to check
the plan (0 to 1 GMAT call, the rest Python), even though the plan was never propagated. In 16 trap episodes the model never
notices the inconsistency of the statement. So `claim_contradicted` for this model measures mostly a loose use of the word
"verified" together with a wrong answer; it supports H5 in its broad form, not a claim of having run a check that failed.
It also means the rate depends on how the prompt defines `verified` (the prompt asks whether and how the answer was checked).

## By line (solved C / solved B / instances), exploratory

```
line                                   lvl  Gemini      gpt-oss     Qwen
circularize_plan/maneuvers               3  1/0/5       4/3/5       3/3/5
finite_burn_raise/finite                 4  0/0/2       3/1/5       0/0/5
frame_trap/maneuvers                     3  0/3/5       5/5/5       3/4/5
guess_trap_transfer/maneuvers            3  1/1/5       5/4/5       1/5/5
hohmann/maneuvers                        3  1/3/5       5/5/5       3/5/5
hohmann/values                           1  4/5/5       2/4/5       4/4/5
hohmann_or_bielliptic_plan/maneuvers     3  1/0/5       3/5/5       1/3/5
j2_drift/values                          2  1/0/5       3/3/5       2/2/5
plane_change_budget_plan/maneuvers       3  0/0/5       0/0/5       0/3/5
plane_change_dv/values                   1  4/4/5       5/5/5       2/5/5
rendezvous_phasing/maneuvers             4  0/0/3       2/2/5       0/4/5
state_at_date/values                     2  3/0/5       5/1/5       4/5/5
sun_synchronous/orbit                    4  0/1/5       4/0/5       2/2/5
tle_state/values                         2  0/0/5       5/4/5       4/2/5
trap_isp/values                          2  0/0/3       0/0/3       0/0/3
trap_period/values                       2  0/0/3       0/0/3       0/0/3
trap_radius/values                       2  1/0/3       0/0/3       0/0/3
```

Where GMAT clearly helps gpt-oss: `sun_synchronous` (4 against 0), `state_at_date` (5 against 1), `finite_burn_raise` (3 against 1).
Nothing helps on `plane_change_budget_plan` (0 for Gemini and gpt-oss in both conditions) or on the three trap lines.
