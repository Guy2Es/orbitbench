# Decision rule for a lunar low-orbit family

Written on 7 November 2026, before any lunar run, GMAT or Python. This text is not edited after the first
measurement. A change goes in "Amendments" with its date and its reason.

## Why

Models rarely call GMAT-MCP when a closed form exists (see `pilot_audit.md` and `test_audit.md`). A lunar family
helps only if offline Python fails on it for lack of data (gravity field, ephemerides), not for lack of skill.
This rule says, before looking at any result, what counts as a failure of the Python baseline.

## Question measured

Date at which the periapsis radius falls below 1737.4 km, for a low lunar orbit (about 100 km altitude,
eccentricity about 0.005, inclination 45 to 85 deg), from a development set of 10 seeds. The seeds are kept apart
from every test seed.

## Reference

GMAT with the lunar field of the highest degree and order that the container really loads (reported, not assumed),
Earth and Sun as perturbers.

## Rules

1. **Reference is usable** only if the impact date moves by less than 0.25 day across three solver settings
   (step and tolerance) on at least 9 of 10 seeds. Otherwise the tolerance of 1 day is not defensible, and the family
   is dropped or reworked.
2. **Baseline fails** (point mass, J2, C22, Earth and Sun with approximate ephemerides) if its impact date differs from
   the reference by more than 1 day on at least 8 of 10 seeds.
3. **Baseline trivially passes** if the gap is under 1 day on at least 5 of 10 seeds. The family is dropped, because
   it would not need the tool.
4. If the baseline fails on 6 or 7 seeds (neither rule 2 nor rule 3), the family is reworked and the rule is applied
   again on 10 new development seeds.
5. **Run time.** If one 60-day reference run exceeds 300 s (the GMAT job limit of `freeze.md`), the horizon is
   shortened before anything else changes.
6. The Python baseline is written once and not tuned after seeing the gap. A second version is allowed only if the
   first has a bug, shown by a check against a known case, and both versions are reported.

## Fallback

If rule 1 or rule 3 ends the lunar family, the drag and re-entry variant (350 km, GMAT density model) is evaluated
with the same rules.

## Amendments

### 7 November 2026: round 1 measured, parameters reworked (rule 4), before round 2

The rules above are unchanged. Round 1 (rng seed 20261107, periapsis altitude 95 to 105 km, eccentricity 0.003 to
0.008, inclination 45 to 85 deg, GRGM900C 50x50, Earth and Sun, horizon 60 days) gave no impact on any of the 10 seeds:
the lowest periapsis radius reached was 1745.2 km (seeds at 54 deg), the others stayed above 1782 km. Three solver
settings (PrinceDormand78 at 1e-12 and 1e-10, RungeKutta89 at 1e-12) agreed to 0.1 km. With no impact date, rules 1 to 3
could not be applied, so rule 4 applies: rework and repeat on 10 new seeds.

Round 2, declared before it runs: rng seed 20261108, periapsis altitude 30 to 60 km, everything else as in round 1.
Rules 1 to 6 apply as written. Seeds without an impact in 60 days count as "no date" for both the reference and the
baseline; a seed counts as a baseline failure if the baseline finds an impact and the reference does not (or the
reverse), or if both do and the dates differ by more than 1 day. Round 1 data are kept and reported.

### 7 November 2026: round 2 result

- Reference (GMAT, GRGM900C 50x50): impact on 6 of 10 seeds, at 5.22, 7.22, 16.07, 46.81, 48.19 and 52.21 days; no impact
  on the other 4 (lowest periapsis radius 1743.3 to 1756.7 km). Three solver settings agree to 0.001 day on all 10
  seeds, so rule 1 holds (10 of 10). One 60-day run takes at most 90 s, under the limit of rule 5.
- Baseline (written once, as in the rule): finds no impact on any seed; its lowest periapsis radius is 1771.8 km or more.
  It fails on the 6 seeds where the reference impacts and agrees ("no impact") on the 4 others: 6 failures of 10.
- Outcome by the rules: 6 failures is neither rule 2 (at least 8 failures) nor rule 3 (at least 5 seeds passing: here
  only 4 pass), so rule 4 applies: rework and repeat on 10 new seeds. The baseline was not validated against a known case
  yet; this is to be done (GMAT with a degree-2 order-2 field, same bodies) before reading the gap as a data effect.

### 7 November 2026: validation of the baseline against GMAT with a degree-2 order-2 field

Same 10 round-2 seeds, GMAT with GRGM900C truncated to degree 2 order 2, Earth and Sun, solver setting S1. Lowest
periapsis radius over 60 days: GMAT 2x2 and the Python baseline agree to 0.1 km or better on all 10 seeds (largest
difference below 0.1 km), and neither finds an impact. With the full 50x50 field, GMAT impacts on 6 of 10 seeds. The
baseline therefore has no visible bug, and its gap to the reference comes from the harmonics above degree 2 (the
mascons), not from its code, its ephemerides or its frames. No second version of the baseline is needed (rule 6).

### 7 November 2026: round 3 declared, before it runs

Rule 4 applies after round 2. Round 3: rng seed 20261109, periapsis altitude 20 to 45 km, eccentricity 0.003 to 0.008,
inclination 45 to 85 deg, GRGM900C 50x50, Earth and Sun, horizon 60 days, 10 new seeds, same three solver settings, same
baseline as in round 2 (unchanged code). Rules 1 to 6 and the counting of "no impact" seeds are as written above. If
rule 4 applies again, the family is reworked once more or dropped; no further change of the thresholds.

### 7 November 2026: round 3 result

- Reference (GMAT, GRGM900C 50x50): impact on 7 of 10 seeds, at 5.40, 6.17, 6.83, 10.87, 12.79, 17.94 and 22.04 days; no
  impact on the other 3 (lowest periapsis radius 1741.1 to 1753.6 km). Three solver settings agree to 0.001 day or better
  on all 10 seeds (rule 1: 10 of 10). Runs take 7 to 102 s (rule 5 holds).
- Baseline (same code as round 2): no impact on any seed; lowest periapsis radius 1763.7 km or more. It fails on the 7
  seeds where the reference impacts and agrees on the 3 others: 7 failures of 10.
- Outcome by the rules: 7 failures is neither rule 2 (at least 8) nor rule 3 (at least 5 passing), so rule 4 applies
  again. As declared, the thresholds are not changed. The 3 seeds without an impact in 60 days are what keeps the count
  below 8: on every seed that has a reference date, the baseline fails (7 of 7 here, 6 of 6 in round 2).

### 8 November 2026: round 4 declared, before it runs (change of the family, not of the thresholds)

Instances of the family must have a reference date, so seeds are drawn with rejection. Procedure, fixed now: rng seed
20261110, periapsis altitude 20 to 45 km, eccentricity 0.003 to 0.008, inclination 45 to 85 deg, GRGM900C 50x50, Earth
and Sun, horizon 60 days. 16 candidates are drawn in order; GMAT (setting S1) is run on each; the first 10 whose
periapsis radius falls below 1737.4 km within 60 days are kept, in drawing order, and nothing else is used to select. If
fewer than 10 of the 16 impact, more candidates are drawn in the same stream. The other two solver settings (rule 1) and
the baseline (same code as rounds 2 and 3) run on the 10 kept seeds. All candidates, kept or rejected, are reported.
Rules 1 to 6 as written: with every kept seed impacting in the reference, a baseline failure is a missing impact or a
date more than 1 day away, and rule 2 needs 8 failures out of 10.

### 8 November 2026: round 4 result

- Screening: the first 10 candidates (indices 0 to 9) all impact in the reference, so all 10 are kept and none was
  rejected among them. Candidates 10 to 15 were also run: 10, 11 and 14 do not impact (lowest periapsis radius 1744.2 to
  1748.7 km), 12, 13 and 15 impact (20.38, 55.90 and 8.16 days); they are not used.
- Reference (GMAT, GRGM900C 50x50), kept seeds: impact at 2.99, 3.73, 3.96, 8.79, 8.92, 9.54, 10.10, 11.32, 29.94 and
  55.27 days. Three solver settings agree to 0.0001 day or better on all 10 seeds (rule 1: 10 of 10). Longest run 77 s
  (rule 5 holds).
- Baseline (same code as rounds 2 and 3): no impact on any of the 10 seeds; lowest periapsis radius 1758.3 km or more.
  It misses all 10 impacts: 10 failures of 10, so rule 2 holds (at least 8 failures). Rules 1 and 2 are met.
- Decision of the plan (step 7): go for the lunar family at these parameters (periapsis altitude 20 to 45 km, 60-day
  horizon, rejection of seeds without a reference impact). Not yet checked: question 2 (the delta-v), the prompt, the
  grader, and whether a model with only Python tries a cleverer baseline than this one.

### 8 November 2026: independent check of the reference (amendment, written after the numbers below were seen)

Until now the reference was GMAT alone. An independent propagator was written with no GMAT code: GRGM900C degree and
order 50 read from grgm900c.cof (Cunningham recursion, checked against the analytic J2 acceleration to 2e-16), Earth and
Sun point masses with positions read from a JPL SPK with jplephem, orientation of the field read from the DE421
libration kernel with jplephem, DOP853 at rtol 1e-12, same stop rule (osculating periapsis radius below 1737.4 km). It
takes only the initial elements of each table row as input.

- Result: on the 15 development seeds (0 to 14) it reproduces every GMAT impact date to 0.0001 day or better, including
  the dates at 47 and 48 days. Replacing DE405 by DE421, or the GM values (file or DE), changes no date by more than 0.0001
  day.
- Two facts about the statement, found by this check. (1) GMAT takes the Earth, Sun and Moon positions from DE405, while
  the statement said DE421: the statement is corrected to DE405 (no effect on any answer). (2) GMAT applies the field in
  the Moon principal-axes frame (NAIF MOON_PA, from the DE421 libration kernel), although GRGM900C is defined in the mean
  Earth / polar axis frame (MOON_ME); the statement was silent on it and now says it.
- Sensitivity to that frame choice: rotating the field by the PA to ME offset (67.92, 78.56 and 0.30 arcseconds, both
  signs, so a change of the order of 100 arcseconds) moves 13 of 15 dates by less than 0.08 day. Seed 10 moves from 32.41
  to 55.19 days with one sign, and 32.34 days with the other; seeds 2, 6, 11 and 12 move by 0.03 to 0.08 day.
- Rule added to the family (the 0.3 day threshold was chosen after seeing that gap: 13 seeds under 0.08 day, one at 22.8
  days): a seed is kept only if its date moves by less than 0.3 day under both signs of the offset above. Seed 10 fails
  it and is replaced, by the next impacting candidate of its own stream, with the same screening applied to that
  candidate. The same rule applies to the private test seeds.
- Limit, stated plainly: a solver without the libration kernel cannot reproduce the orientation exactly; the 1 day
  tolerance is what keeps the task fair. Before screening, a 100 arcsecond change stays inside 1 day on 14 of 15 seeds.
  After replacing seed 10, the screened table has to be rechecked the same way (not done at the time of this entry).

### 8 November 2026: seed 10 replaced, screened table checked

- Seed 10 was rebuilt with scripts/build_lunar_table.py --redo 10: candidate 0 of its stream is skipped (rejected = 1) and
  candidate 1 impacts at 10.8104 days (GMAT, setting S1).
- Independent propagator on this row: 10.8104 days (difference below 0.0001 day); with the two signs of the orientation
  offset: 10.8104 and 10.8104 (shifts below 0.0001 day). It passes the 0.3 day rule.
- The other 14 rows were not changed. Their largest shift under the offset is 0.0737 day (seed 12), so all 15 rows of
  the table (seeds 0 to 14) pass the 0.3 day rule.
- The check is kept as scripts/validate_lunar_reference.py (needs the .cof, the SPK and the PCK files, see its header).

### 8 November 2026: private test seeds drawn and screened

The 30 test seeds of the family are one range of consecutive integers, drawn at random on this date and kept in
`private/lunar_impact_table.yaml` (git-ignored). Their identifiers are not given here; they are referred to by their last
three digits.

- Built with GMAT (setting S1): 30 of 30 impact within 60 days, the table rows have 0 to a few skipped candidates.
- Independent propagator on all 30 rows: it reproduces every GMAT date to 0.0001 day or better.
- Orientation screen (0.3 day rule): 26 seeds shift by 0.08 day or less. Four fail: seed ..486 (the impact disappears
  under one sign), ..488 (19.0 days), ..508 (1.5 days) and ..510 (0.83 day).
- The four were replaced, each by the next impacting candidate of its own stream (`--redo`), and the replacements were
  screened the same way: all four pass, with shifts of 0.001 day or less (9.33, 7.48, 54.03 and 13.03 days).
- Result: 30 seeds, all verified by the independent propagator and all inside the 0.3 day rule. No other selection was
  applied. The failing candidates are not used and are not reported with results.
