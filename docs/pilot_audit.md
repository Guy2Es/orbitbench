# Pilot audit

Two runs with Claude Haiku 5.5 on development seeds, and a Haiku-versus-Sonnet 5.5 comparison on one seed per line.
Every episode that was not solved was read in its Inspect transcript. The runs had 12 failed episodes; the aim of 30
was dropped on purpose (see the end).

Causes: **model** = the model's mistake, task and grader are right; **budget** = the spending guard of 150 000 tokens
per episode ended the episode (the guard is not one of the declared limits, see `freeze.md`).

| Run | Episode | Condition | Grader label | Cause | Evidence | Action |
|---|---|---|---|---|---|---|
| smoke | `plane_change_dv:values:0` | B | `values_mismatch` | model | wrong value in one reply | none |
| pilot | `state_at_date:values:0` | B, C | `values_mismatch` | model | the reference equals an independent DOP853 integration (to 1e-4 km); both replies start from a wrong epoch state, then agree with each other | none |
| pilot | `frame_trap:maneuvers:0` | C | `constraints_violated` | model | right Δv (1.0449992), written as 0.0010449992 km/s in LVLH, a unit slip: apoapsis stays at 15 656 km | none: this is the trap |
| comparison | `circularize_plan:maneuvers:0` | B (Haiku) | `constraints_violated` | model | burn at the periapsis (M = 360°) described as the apoapsis; eccentricity 0.464; inclination and Δv met | none |
| pilot, comparison | `plane_change_budget_plan:maneuvers:0`, `:1` | B, C | `limit_token` | model, budget | Haiku loops on `np` undefined and re-derivations (9 turns, 150 000 tokens, then 16 turns, 403 000 in the comparison); Sonnet solves it in 4 turns | guard raised for the final run |
| pilot | `circularize_plan:maneuvers:1`, `hohmann_or_bielliptic_plan:maneuvers:1` | C | `limit_token` | budget | 7 turns, 159 000 to 162 000 tokens: about 32 000 tokens of tool descriptions are read again at every turn in condition C | guard raised for the final run |

## Findings

- No defect of the task, the grader or the harness. No correction was needed in the code, and none of the
  reference values was changed.
- `react()` ends on `<final_answer>` in both conditions; the labels `limit_token` and `constraints_violated` are right.
- In condition C the models almost never call a GMAT tool: 6 GMAT calls in 44 pilot episodes, none in the 22 comparison
  episodes. The tasks have closed forms that a model can write in Python, and the grader does not look at the session.
  The difference C minus B is therefore expected to be near zero in v0.1; v1.0 adds tasks that need the simulation.
- A token guard of 150 000 tokens, counted over all calls with cache reads, ends episodes after 6 to 9 turns in
  condition C, long before the 60-message limit. It must not be what ends an episode in the published run.

## Why fewer than 30 failures

The aim of 30 audited failures was meant to find defects of the benchmark. Haiku produced 12, all of them mistakes of
the model, and Sonnet 5.5 solved all 22 episodes of the comparison. Running more cheap episodes only to reach 30 would
not find new kinds of defects. The audit is stated as it is: 12 failures read, 0 benchmark defects.
