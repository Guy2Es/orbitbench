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

### Second round: seeds 5 to 9, and Sonnet on level 4

Haiku on development seeds 5 to 9 of the level-4 lines, then Sonnet on seeds 0 to 4 (a level-4 line has only five
instances, so `--per-line 10` adds nothing beyond them). Same limits as above.

| Line | Haiku B (seeds 0-9) | Haiku C (seeds 0-9) | Sonnet B (seeds 0-4) | Sonnet C (seeds 0-4) |
|---|---|---|---|---|
| `sun_synchronous` | 10/10 | 10/10 | 5/5 | 5/5 |
| `finite_burn_raise` | 10/10 | 10/10 | 5/5 | 5/5 |
| `rendezvous_phasing` | 7/10 | 7/10 | 5/5 | 5/5 |

Level 4 is saturated for Sonnet, and for Haiku on two of its three lines. C costs two to three times the tokens of B
for Sonnet with no gain in success.

## Failures read one by one

| Line | Cond. | Label | Cause | Evidence |
|---|---|---|---|---|
| `rendezvous_phasing` | B | `constraints_violated` | model | the burns are written in km/s with a factor 1000 missing (0.000146 instead of 0.1465); the reply's own check claims 0.7 m of error |
| `rendezvous_phasing` | C | `constraints_violated` | model | an independent integration of the plan gives 12 082 km at the final epoch, as the grader; the reply claims 0.07 m |
| `rendezvous_phasing` | B | `wrong_status` | model | declares the task infeasible (minimum 3725 m/s against 1785 m/s); the reference plan, two burns at the two allowed epochs, fits the budget |
| `rendezvous_phasing` | B, C | `wrong_status` (2) | model | the Lambert enumeration is incomplete, so the model concludes the task is infeasible; a feasible plan exists (seeds 5 to 9) |
| `rendezvous_phasing` | B or C | `constraints_violated` | model | the burns are in m/s where km/s is asked, a factor 1000 (seeds 5 to 9); the detector flags the contradicted claim |
| `trap_radius` | B, C | `missed_trap` | model | the statement gives the Earth's radius (6378 km) and a target radius of about 4500 km; the replies compute the transfer |
| `trap_altitude` | B, C | `missed_trap` | statement | the first orbit was written "of radius" and the second "at X km": reading a radius was natural. Reworded so both are "at X km", with the same result for both models: a distance given alone is read as a radius, so the kind was replaced |

## Changes made

- `trap_altitude` replaced by `trap_period`: the target orbit is given by its radius and its period, and the trap's
  period is 15 % off the one the radius implies (the twin's agrees). The line now separates the models (Haiku 2/3,
  Sonnet 3/3) and the twin is solved 3/3.
- Nothing else was changed. No grader, reference or tolerance defect was found.

## Hardening of the two saturated lines

Both were made harder, because a floor line says nothing about the conditions:

- `sun_synchronous`: the tolerance on the node drift goes from 0.02 to 0.001 deg/day. The secular formula is off by
  0.002 to 0.005 deg/day once the orbit is integrated, so it no longer passes; instances whose formula would pass, or is
  more than 0.015 deg/day away, are redrawn. GMAT and the numerical reference agree to 0.00025 deg/day on five seeds.
- `finite_burn_raise`: two finite burns, the second circularizing at the new apoapsis, with the periapsis radius also
  checked (1 % on both radii, the inclination as before). A prograde burn of over a thousand seconds cannot make the
  orbit exactly circular: the reference, with its start and duration found by integration, misses by 0.4 to 0.5 %, so
  the tolerance leaves a factor two. Apoapsis factor 1.2 to 1.45, and the two burns must fit in 90 % of the tank. In
  GMAT the reference is solved on five seeds; the first burn alone, the impulsive duration, and an impulsively sized
  second burn all fail.

A pilot of these versions, run outside Inspect with the same sandboxes, prompts and grader but another agent loop
(forty episodes, seeds 0 to 4, Haiku and Sonnet, B and C), is a calibration only: its rates are not comparable with the
runs above and are not results.

| Line | Haiku B | Haiku C | Sonnet B | Sonnet C |
|---|---|---|---|---|
| `sun_synchronous` | 5/5 | 4/5 | 4/5 | 5/5 |
| `finite_burn_raise` | 4/5 | 5/5 | 5/5 | 5/5 |

37 of 40. The three failures are model errors: a simulation of the second burn that departs from GMAT (the model
claims its sides agree, GMAT measures 8731 and 12685 km for 10500 km), and two integrations solved exactly on the Sun's
rate in the model's own propagator which GMAT measures 1.1 and 1.6 times the tolerance away. B and C do not differ.
These transcripts were read from their final replies only.

Decision: level 4 stays as it is. If C gives no gain at the end, H1 and H3 are reported as exploratory.

## Third round: the other lines, seeds 5 to 9, conditions B and A

Haiku, run outside Inspect (same sandboxes, prompts and grader, another agent loop; a calibration, not a result), on
the lines not yet read at these seeds. 103 episodes, no technical error.

| Line | B | A (levels 1 and 2 only) |
|---|---|---|
| `hohmann` (values / maneuvers) | 5/5, 4/5 | 5/5 |
| `plane_change_dv` | 5/5 | 5/5 |
| `state_at_date` | 5/5 | 5/5 |
| `j2_drift` | 5/5 | 0/5 |
| `tle_state` | 5/5 | 0/5 |
| `hohmann_or_bielliptic_plan`, `plane_change_budget_plan`, `rendezvous_phasing` | 5/5 each | |
| `circularize_plan`, `frame_trap`, `guess_trap_transfer` | 3/5, 4/5, 4/5 | |
| `trap_radius` / `trap_isp` / `trap_period` | 0/3, 3/3, 2/3 | 0/3, 3/3, 1/3 |

Without tools the closed-form lines (`hohmann`, `plane_change_dv`, `state_at_date`) are still solved, and the two lines that
need a numerical propagation are not: A separates the lines that need a computation from those that do not.

Failures read (the final reply and the graded checks; the transcripts were not read whole):

| Line | Cond. | Label | Cause | Evidence |
|---|---|---|---|---|
| `hohmann` maneuvers | B | `constraints_violated` | model | the second burn is dated off the apoapsis: the orbit stays eccentric (0.54) at 26 686 km instead of 22 354 km |
| `circularize_plan` | B | `constraints_violated` | model | the apoapsis time from Kepler's equation is wrong, the burn leaves an eccentricity of 0.83; the reply says it is not replayed |
| `circularize_plan` | B | `constraints_violated` | model | the burn is written 0.0011296 km/s where its own text says 1.129644 km/s, a factor 1000; the reply claims verified, which the detector flags as contradicted |
| `guess_trap_transfer` | B | `constraints_violated` | model | the second burn is retrograde and the orbit stays at 11 690 km instead of 20 652 km |
| `frame_trap` | B | `constraints_violated` | model | the burn is written 0.00123 km/s in LVLH where its text says 1230 m/s, a factor 1000; claimed verified, flagged |
| `trap_radius` (3 B, 3 A) | B, A | `missed_trap` | model | as in the first round: the transfer is computed to an orbit below the surface |
| `trap_period` (1 B, 2 A) | B, A | `missed_trap` | model | in B the model notes the stated period is inconsistent with the radius and answers anyway, with status `solved` |
| `j2_drift`, `tle_state` (10) | A | `values_mismatch` | no tool | hand secular rates, short-period terms and SGP4 omitted; the replies say the tolerance may not be met (`verified: false`) |

Two patterns stand out: a factor 1000 between m/s and km/s in a plan (twice here, once in the first round), and a trap
noticed but not declared, which the rules count as missed. No grader, reference or tolerance defect was found.

About 45 failures have been read in all (the plan asks for at least 30).

## Epoch window of the J2 lines

GMAT's Earth axis is the z axis of the inertial frame only near J2000. The reference inclination of `sun_synchronous`
seed 0, flown in GMAT from six epochs over the same span, gives a drift that departs from the Sun's rate by:

| Epoch | Drift minus Sun's rate (deg/day) |
|---|---|
| 01 Jan 2000 12:00 | -0.00009 |
| 01 Jan 2005 12:00 | -0.00035 |
| 01 Jan 2010 12:00 | -0.00101 |
| 01 Jan 2020 12:00 | -0.00207 |
| 01 Jan 2026 00:00 | -0.00255 |
| 01 Jan 2035 12:00 | -0.00383 |

The error grows by about 0.0001 deg/day per year. With the tolerance of 0.001 deg/day and a margin of four, the epoch
must stay within two years of J2000: the J2 lines (`sun_synchronous`, `j2_drift`) keep `01 Jan 2000 12:00:00.000`, which
is fixed in the freeze.

## Still open

- `trap_isp` is at 100 % for both models and has not been hardened.
- About 21 failures are audited so far (the plan asks for at least 30 before the freeze).
- The false-claim detector flagged the two wrong `rendezvous_phasing` plans (`claimed_verified` and `claim_contradicted`)
  and, by its rules, not the `wrong_status` one. The 50-transcript hand validation is still to do.
- Human review of the new statements and the outside-written tasks remain to be organised by the maintainer.
