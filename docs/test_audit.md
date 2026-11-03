# Audit of the failures on the test seeds

Claude Haiku 5.5, conditions B and C, 61 instances each, the frozen values of `freeze.md`. Thirteen episodes were
not solved (8 in B, 5 in C). Each was read in its Inspect transcript, and the reference of every values-mode failure
was recomputed by an independent integration that shares no code with the benchmark. Instances are named by line,
never by seed.

| Condition | Line | Grader label | Cause | Evidence |
|---|---|---|---|---|
| B | `circularize_plan` | `constraints_violated` | model | negative tangential burn at the apoapsis: the reply says the apoapsis speed is below the circular speed and still brakes; the eccentricity check fails |
| B | `guess_trap_transfer` | `constraints_violated` | model | the statement asks for burns along the velocity; the reply puts a normal component in the second VNB burn, so the inclination leaves 18.4 deg |
| B | `j2_drift` (3 instances) | `values_mismatch` | model | an independent J2 integration with the constants of the statement matches the reference to 1e-5 deg; the replies are off by 0.06 to 0.27 deg in the periapsis argument (tolerance 0.02 deg) |
| B | `plane_change_budget_plan` | `wrong_status` | model | the reply declares the task ill posed, claiming 3.7234 km/s is the minimum; the reference splits the plane change over the two burns and needs 3.6265 km/s, within the budget of 3.6285 km/s |
| B | `state_at_date` (2 instances) | `values_mismatch` | model | the reference equals an independent DOP853 integration to 1e-6 km; the replies are off by hundreds to thousands of km, the cause was not identified |
| C | `j2_drift` | `values_mismatch` | model | independent integration matches the reference; the periapsis argument is off by 0.68 deg |
| C | `plane_change_budget_plan` (2 instances) | `limit_token` | model, guard | 22 turns and no `<final_answer>`; the guard of 1 000 000 tokens ended the episodes, not the 60-message limit |
| C | `plane_change_dv` | `values_mismatch` | model | arithmetic slip: mu / r is written as 12 877 instead of 12.877 km^2/s^2, so the velocity is 113 km/s |
| C | `state_at_date` | `values_mismatch` | model | independent integration matches the reference |

## Claude Sonnet 5.5 (same instances, same frozen values)

Two episodes of 122 were not solved, both in condition C and both read in their transcripts.

| Condition | Line | Grader label | Cause | Evidence |
|---|---|---|---|---|
| C | `state_at_date` | `values_mismatch` | model | the reply propagates the point-mass orbit with Kepler's equation in Python, the method the statement asks for, and writes numbers thousands of km from the reference; the reference was checked against an independent integration for this family; the slip was not located |
| C | `tle_state` | `invalid_format` | model | the `<final_answer>` block closes its object after `values`, then continues with `"claims"`: the JSON is invalid (extra data), so the grader rejects it as the format requires |

## Findings

- None of the 13 failures comes from a defect of a task, of the grader, of a reference or of the harness. Nothing was
  changed, and the frozen values hold.
- `j2_drift` is the line Haiku misses most: 3 of 5 in B and 1 of 5 in C. Its tolerance (0.02 deg) is tight for an
  osculating periapsis argument several days later. The reference was checked twice, so the tolerance stays; the cause
  of the models' deviations was not identified.
- Two episodes in C ended on the token guard, not on a declared limit. They are counted as failures, and the guard is
  reported with the results.
- In condition C, 9 of 61 episodes called a GMAT tool (60 calls): 3 on `guess_trap_transfer`, 2 on
  `hohmann_or_bielliptic_plan` and 4 on `plane_change_budget_plan`, the lines that invite a corrector or a search.
  The other 52 used Python only.
