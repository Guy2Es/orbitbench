# Results of the lunar line (v1.1), test seeds

Reported as a result on this line only, as declared on 8 November 2026 (`docs/hypotheses.md`). The line is a separate stratum
of v1.1: v1.0 is unchanged and its numbers (`docs/results_v10.md`) do not include it.

## Setup

- Line `lunar_impact` (level 4): the date, within 1 day, at which a low lunar orbit (periapsis altitude 20 to 45 km,
  eccentricity 0.003 to 0.008, inclination 45 to 85 deg) falls to the surface within 60 days, with the GRGM900C field
  (degree and order 50), Earth and Sun. The answer needs data (high-degree lunar harmonics, ephemerides) that a model can
  neither recall nor fetch offline. On the development seeds the Python baseline (point mass, J2, C22, approximate
  ephemerides) found no impact where GMAT did, and agreed with GMAT truncated to degree 2 to 0.1 km: the gap comes from the
  harmonics above degree 2, not from a bug (`docs/lunar_baseline_rule.md`).
- 30 test seeds, screened (the date moves by less than 0.3 day under a change of the Moon orientation), still private.
- Conditions B and C (A is not run: the task cannot be answered from memory). k = 3 attempts per instance, so 90 episodes
  per cell, message limit 60, token guard 1 000 000 per episode.
- Models: gpt-oss-120b (Crusoe), Gemini 2.5 Flash Lite, Qwen3.7 Flash, through OpenRouter. DeepSeek V4 Flash has no score:
  its condition C stopped on an image-input error of its pinned provider (see `docs/freeze.md`, 9 November 2026); the 13
  partial episodes it logged are not counted.
- Spend of the run: about 4 USD.

## Results

Solved (every constraint met), 95 % Wilson interval. Reward equals the solved share on this line.

| Model | B | C | C minus B (paired hierarchical bootstrap, 95 %) |
|---|---|---|---|
| gpt-oss-120b | 0/90 (0 to 4 %) | 52/90 (47 to 67 %) | +0.578 (+0.467 to +0.689) |
| Gemini 2.5 Flash Lite | 0/90 (0 to 4 %) | 39/90 (34 to 54 %) | +0.433 (+0.356 to +0.511) |
| Qwen3.7 Flash | 0/90 (0 to 4 %) | 53/90 (49 to 68 %) | +0.589 (+0.467 to +0.700) |

Instances solved in all 3 attempts (H4 on this line): B 0 for all three; C gpt-oss-120b 0.233 (0.100 to 0.400), Gemini 0.033
(0.000 to 0.100), Qwen 0.233 (0.100 to 0.400).

Outcome of the 90 episodes of each cell (labels of the grader; the failures were not read one by one):

| Model, condition | solved | refused (`ill_posed`) | wrong answer | no usable answer |
|---|---|---|---|---|
| gpt-oss-120b B | 0 | 74 | 1 | 15 |
| gpt-oss-120b C | 52 | 0 | 7 | 31 |
| Gemini B | 0 | 61 | 0 | 29 |
| Gemini C | 39 | 2 | 3 | 46 |
| Qwen B | 0 | 4 | 5 | 81 |
| Qwen C | 53 | 0 | 2 | 35 |

Claims in C: `claimed_verified` 58 (gpt-oss-120b, 7 contradicted), 42 (Gemini, 3), 24 (Qwen, 0); in B one Qwen episode
claimed verification and was contradicted. No `claim_unchecked` and no `claim_unconverged`.

## Reading

1. **Where the answer needs data that Python does not have, the tool is indispensable.** No model solves any of the 270 B
   episodes, and 39 to 53 of 90 C episodes are solved per model. The paired differences are +0.43 to +0.59, with intervals far
   from zero. In B the two models that stop early mostly say that the data is missing (74 and 61 refusals of 90).
2. **It qualifies the conclusion of v1.0**, where the paired differences were +0.11, 0.00 and -0.23 and the value of the tool
   was not established: v1.0 is made mostly of tasks that Python alone can solve, which dilutes the effect. The lunar line is
   built so that Python alone fails, so it shows that the benchmark detects the value of the tool when the tool brings what
   Python lacks, not that the tool is better in general. B here is not a fair head-to-head: it has no access to the data.
3. **Qwen no longer loses with the tool.** Its -0.23 in v1.0 came from episodes that never answer; here the tool is needed and
   its C (53 of 90) is on par with gpt-oss-120b's (52 of 90).
4. **The tool is not enough.** In C, single-attempt success is 43 to 59 %, only 3 to 23 % of the instances are solved in all
   3 attempts (H4 supported on this line), and 31 to 46 of 90 episodes end without a usable answer (limits, loops, empty
   replies), as in v1.0.

## Limits

One line, 30 instances with 3 attempts each (the 90 episodes of a cell are not independent). The line was designed so that B
fails. The failures were declared to be read one by one and have not been: the table uses the grader's labels. DeepSeek V4 Flash
has no score. The test seeds of this line are private until it is published.

## Reproduce

`python -m orbitbench.harness analyze runs/lunar-test-gptoss-B runs/lunar-test-gptoss-C runs/lunar-test-geminilite-B
runs/lunar-test-geminilite-C runs/lunar-test-qwenflash-B runs/lunar-test-qwenflash-C` (the run folders are not in the
repository; `scripts/run_lunar_test.py` reruns the steps).
