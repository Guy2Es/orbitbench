# Calibration pilot of the v1.0 families

Claude Haiku 5.5 (and Claude Sonnet 5.5 on the traps), development seeds 0 to 4 (traps: 0 to 2), one attempt, no
batch, token guard of 1 000 000. Nothing here uses a test seed. Pilot runs: `runs/pilot10-*` (not in the repository).

## Success rates

| Line | Haiku B | Haiku C | Sonnet B |
|---|---|---|---|
| `sun_synchronous` | 5/5 | 5/5 | |
| `finite_burn_raise` | 5/5 | 5/5 | |
| `rendezvous_phasing` | 3/5 | 4/5 | |
| `trap_radius` | 0/3 | 0/3 | 1/3 |
| `trap_isp` | 3/3 | 3/3 | 3/3 |
| `trap_altitude` (first wording, then reworded) | 0/3, 0/3 | 0/3 | 0/3 |
| `trap_period` (replaces `trap_altitude`) | 2/3 | | 3/3 |
| twins (`radius`, `isp`, `altitude`) | 3/3 each | | |
| `trap_period_twin` | 3/3 | | |

Twins solved 3/3 each: no false alarm in this sample.

## Failures read one by one

| Line | Cond. | Label | Cause | Evidence |
|---|---|---|---|---|
| `rendezvous_phasing` | B | `constraints_violated` | model | the burns are written in km/s with a factor 1000 missing (0.000146 instead of 0.1465); the reply's own check claims 0.7 m of error |
| `rendezvous_phasing` | C | `constraints_violated` | model | an independent integration of the plan gives 12 082 km at the final epoch, as the grader; the reply claims 0.07 m |
| `rendezvous_phasing` | B | `wrong_status` | model | declares the task infeasible (minimum 3725 m/s against 1785 m/s); the reference plan, two burns at the two allowed epochs, fits the budget |
| `trap_radius` | B, C | `missed_trap` | model | the statement gives the Earth's radius (6378 km) and a target radius of about 4500 km; the replies compute the transfer |
| `trap_altitude` | B, C | `missed_trap` | statement | the first orbit was written "of radius" and the second "at X km": reading a radius was natural. Reworded so both are "at X km", with the same result for both models: a distance given alone is read as a radius, so the kind was replaced |

## Changes made

- `trap_altitude` replaced by `trap_period`: the target orbit is given by its radius and its period, and the trap's
  period is 15 % off the one the radius implies (the twin's agrees). The line now separates the models (Haiku 2/3,
  Sonnet 3/3) and the twin is solved 3/3.
- Nothing else was changed. No grader, reference or tolerance defect was found.

## Still open

- Lines at 100 % for Haiku in both conditions: `sun_synchronous`, `finite_burn_raise`, `trap_isp`. They are kept as
  floor lines for now; whether to harden them is decided after Sonnet and the full set of 85 instances.
- Fewer than 30 failures are audited so far (the plan asks for at least 30 before the freeze): the pilot gave 15 plus
  the twins, and the audit continues with the remaining dev seeds.
- The false-claim detector flagged the two wrong `rendezvous_phasing` plans (`claimed_verified` and `claim_contradicted`)
  and, by its rules, not the `wrong_status` one. The 50-transcript hand validation is still to do.
- Human review of the new statements and the outside-written tasks remain to be organised by the maintainer.
