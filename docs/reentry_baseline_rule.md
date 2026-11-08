# Decision rule for a re-entry (atmospheric drag) family

Written on 8 November 2026, before any run of GMAT or of the Python baseline for this family. This text is not edited
after the first measurement. A change goes in "Amendments" with its date and its reason.

## Why

The lunar family helps because a model with only Python lacks data it cannot recall or download (the gravity field).
The atmosphere is another such barrier: the density a model can write from memory is a standard-atmosphere table, while
the density the reference uses depends on the solar flux, the season and the latitude. This rule says, before looking at
any result, what counts as a failure of the Python baseline, as in `lunar_baseline_rule.md`.

## Question measured

Time, in days since the epoch, at which a spacecraft in a low, nearly circular Earth orbit first falls below a geodetic
altitude of 120 km. Development set: 10 seeds, kept apart from every test seed.

## Reference

GMAT, Earth gravity JGM-3 degree and order 8, no third body and no solar pressure, atmosphere MSISE90 with F10.7 = F10.7A
= 150 and Kp = 3 held constant (setting of the existing compiler), spacecraft mass 800 kg, drag area 4 m2, Cd 2.2,
PrinceDormand78 at accuracy 1e-12, steps of at most 60 s. Stop: the Earth altitude parameter of GMAT equal to 120 km.

## Draw

Random seed 20261201. Periapsis altitude 185 to 215 km, eccentricity 0.0005 to 0.002, inclination 30 to 98 deg, node,
argument of periapsis and true anomaly uniform, epoch uniform in 2026. Horizon 20 days. Seeds are drawn with rejection:
the first 10 candidates, in drawing order, whose reference reaches 120 km within the horizon are kept; the others are
reported and not used.

## The Python baseline (written now, once)

Point mass and J2 (J2 = 1.08262668e-3, radius 6378.137 km, GM = 398600.4415 km3/s2), the atmosphere co-rotating with the
Earth (7.292115e-5 rad/s), drag acceleration -0.5 rho Cd (A/m) |v_rel| v_rel. The density is the US Standard Atmosphere
1976, interpolated linearly in log density between these altitudes (km: kg/m3): 100: 5.604e-7, 110: 9.708e-8,
120: 2.222e-8, 130: 8.152e-9, 140: 3.831e-9, 150: 2.076e-9, 160: 1.233e-9, 180: 5.464e-10, 200: 2.789e-10,
250: 7.248e-11, 300: 1.916e-11, 350: 5.297e-12, and the density of the nearest end beyond them. Altitude is geodetic
on the ellipsoid of flattening 1/298.257223563. Integration with DOP853 at rtol 1e-10. It sees only the initial elements and
the statement's constants. It is not tuned after seeing the gap.

## Rules

A seed is a baseline pass if its date is within max(5 % of the reference date, 0.1 day) of the reference date, and that
is also the tolerance of the family.

1. **Reference is usable** only if the date moves by less than 2 % across three solver settings (PrinceDormand78 at
   1e-12 with steps of at most 60 s, PrinceDormand78 at 1e-10 with 120 s, RungeKutta89 at 1e-12 with 60 s) on at least
   9 of 10 seeds.
2. **Baseline fails** if it is outside the tolerance on at least 8 of 10 seeds. Then the family is built.
3. **Baseline trivially passes** if it is inside the tolerance on at least 5 of 10 seeds. The family is dropped.
4. If it fails on 6 or 7 seeds, the family is reworked once (a different altitude range or a tighter tolerance, declared
   before the new round) and the rule is applied on 10 new seeds.
5. **Run time**: if one reference run exceeds 300 s, the horizon is shortened first.
6. The baseline is written once. A second version is allowed only for a bug shown by a check against a known case, and
   both versions are reported.

## Known limit, stated before measuring

No independent atmosphere model is available offline here that reproduces GMAT's MSISE90 within the tolerance. Unlike the
lunar family, the reference cannot be checked by a second propagator: the answer is defined by GMAT's implementation of
MSISE90 with the stated constants, and the statement must say so. The three solver settings check the integration, not
the model. If this family is built, that limit is written in its results; whether to include it is the maintainer's
decision, and this rule does not decide it.

## Amendments

### 8 November 2026: round 1 result

Run as declared above (random seed 20261201; the first 10 of 24 drawn candidates all reach 120 km within 20 days, so
none was rejected; the other 14 were not run on the baseline results used here).

- Reference (GMAT, MSISE90, F10.7 150, Kp 3): lifetimes 1.87 to 5.66 days. The three solver settings agree to the printed
  precision (0.000 %) on all 10 seeds: rule 1 holds (10 of 10 under 2 %). Longest set of runs 156 s for 24 candidates on
  4 containers, so rule 5 holds.
- Python baseline (written once, checked against the analytic decay of a circular orbit in constant density, which it
  reproduces to the printed precision with J2 and the rotation of the atmosphere switched off): errors against the reference
  of -1.3, +13.0, +8.5, +2.9, +4.4, -5.3, -5.4, +9.4, +8.8 and +10.6 %. Inside the tolerance (5 %, at least 0.1 day) on
  seeds 0, 3, 4 and 5; outside on 6 seeds.
- Outcome by the rules: 6 failures out of 10 is neither rule 2 (at least 8) nor rule 3 (at least 5 passes), so rule 4
  applies: rework once, or stop. The thresholds are not changed.
- What the numbers say. A standard-atmosphere table, with no data about the solar activity, lands within 13 % of MSISE90 on
  every seed and within 5 % on 4 of 10. Unlike the lunar family, where the baseline finds no impact at all, here a model
  without the tool gets close, and the only way to make it fail more often is a tighter tolerance. A tighter tolerance
  would test whether the answer reproduces GMAT's implementation of MSISE90, which cannot be checked independently (see
  "Known limit"), rather than whether the model has the data.
- Recommendation of the author of this entry, not a decision: stop here and do not add a re-entry family to the release.
  If the maintainer asks for the rework of rule 4, it must be declared here, with its tolerance, before any new seed
  is drawn.
