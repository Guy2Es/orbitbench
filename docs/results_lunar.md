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
- Models: gpt-oss-120b (Crusoe), Gemini 2.5 Flash Lite, Qwen3.7 Flash, through OpenRouter.
- Spend of the run: about 4 USD.

## Results

Solved (every constraint met), with a 95 % bootstrap interval that resamples the 30 instances and keeps the three attempts of an
instance together (the 90 episodes of a cell are not independent). Where no episode is solved (B), the upper bound is the Wilson
bound on 30 instances.

| Model | B | C | C minus B (paired hierarchical bootstrap, 95 %) |
|---|---|---|---|
| gpt-oss-120b | 0/90 (0 to 11 %) | 52/90 (47 to 69 %) | +0.578 (+0.467 to +0.689) |
| Gemini 2.5 Flash Lite | 0/90 (0 to 11 %) | 39/90 (36 to 51 %) | +0.433 (+0.356 to +0.511) |
| Qwen3.7 Flash | 0/90 (0 to 11 %) | 53/90 (48 to 70 %) | +0.589 (+0.467 to +0.700) |

Instances solved in all 3 attempts (H4 on this line): B 0 for all three; C gpt-oss-120b 0.233 (0.100 to 0.400), Gemini 0.033
(0.000 to 0.100), Qwen 0.233 (0.100 to 0.400).

Outcome of the 90 episodes of each cell (labels of the grader; the failures are read one by one in the section below):

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

## The failures, read one by one

Read on 10 November 2026: the 126 episodes of condition C that are not solved, and the 270 of condition B. The transcripts
(tool calls, tool results, last message) were read, not only the labels. "Right number" below means within 1 day of a
reference that the grader does not store: the 30 instances all have solved episodes, those agree to 0.46 day at most, and
their answer serves as the reference. The elements of the orbit were copied correctly in every episode that created a
spacecraft, except one (Qwen), and the force model is the same in failures and successes except for the lunar field (see point 3).

| Why the 126 episodes of C are not solved | gpt-oss-120b | Gemini 2.5 Flash Lite | Qwen3.7 Flash | Total |
|---|---|---|---|---|
| Right number, rejected by the strict format | 16 | 11 | 2 | 29 |
| Wrong number and wrong format | 1 | 4 | 0 | 5 |
| No answer: message limit (60) reached while stepping by hand | 14 | 0 | 33 | 47 |
| No answer: the turn ends early (empty reply, plan or invented tool output, stop after a tool error) | 0 | 31 | 0 | 31 |
| Wrong value after a complete run | 7 | 3 | 2 | 12 |
| Gave up with `ill_posed` | 0 | 2 | 0 | 2 |
| **Not solved** | **38** | **51** | **37** | **126** |

1. **29 of the 126 failures hold the right number.** The reply is not accepted: bare JSON without the `<final_answer>` tags,
   harmony tokens in the reply, the tag not closed, text after the block (gpt-oss, 16), JSON in a markdown fence inside the
   block (Gemini, 13 of its 15 format failures). The strict parser was declared in advance and the result above keeps it. If
   the format were forgiven, C would be 68, 50 and 55 of 90 instead of 52, 39 and 53. This is a sensitivity reading made after
   the fact, not a result.
2. **78 episodes give no answer, in two different ways.** gpt-oss (14) and Qwen (33) do not use the stop condition of the
   tool for the whole run: they step by hand ("propagate one day, read the periapsis, again"), recreate the spacecraft and the
   propagator, reset the session, and hit the 60 messages. Among the solved episodes 98 % to 100 % use `stop_quantity` at
   once; among the failures 55 % (Gemini), 82 % (gpt-oss) and 86 % (Qwen) do, with 2 to 4 times more `propagate` calls. Qwen
   recreates the spacecraft twice or more in 92 % of its failures (45 % of its successes). Gemini (31) never gets that far: its
   reply is empty after `set_mission` or `create_spacecraft` (10) and the loop ends, it describes a call or writes the output
   it expects instead of calling the tool (6), it calls `propagate` with a propagator name that does not exist and stops on the
   error (8), or it stops after the result with a sentence "let me convert" (7).
3. **12 wrong values, of which 3 come from the tool.** `propagate` returned after 30 days when 60 were asked (a default
   `max_days` of 30; the result carries a `warning` field that says so, but it comes last). Two gpt-oss episodes and one Qwen episode then added only the last
   segments and lost the first 30 days (errors of -29.9, -30.0 and -30.0 days). A fourth, gpt-oss, lost its first day-long
   steps the same way (-1.0). Qwen's other error (+12.7) is a step by hand that passed the crossing, so that the stop
   condition fired on a later one. Gemini: one value invented after a `propagate` that returned 0 s ("inferred from partial
   results"), two estimates from a backward propagation. Two gpt-oss episodes, where a single `propagate` stopped 9 and 19 days early, come from the default lunar field: without
   `gravity_file`, `create_propagator` uses LP165P, not the GRGM900C of the statement (the answer of the call names the field).
   gpt-oss omitted it in 36 of its 90 C episodes (17 unsolved, 19 solved). Replayed in GMAT with GRGM900C, the first stops at
   12.17 days (the reference) and the second reaches the 30-day bound before the impact at 37.1 days.
4. **2 episodes give up.** Gemini called a `propagate` that exceeded the 60 s of a call (the job goes on in the background,
   `get_job_status` gives the result) and answered `ill_posed` instead of waiting.

Condition B. gpt-oss and Gemini call no tool in any of their 180 episodes: they answer at once. Of their 135 refusals, every
one says that the GRGM900C coefficients are not available in the environment, and most add the ephemerides or the libration
kernel. The reply is honest, and the grader counts it as a failure (status `ill_posed` for a task that has an answer), so a B
of 0 on this line measures the missing data as much as the reasoning. Qwen is the only one to try: 81 of its 90 episodes use
Python, 69 end on the 60 messages, 5 give a wrong value and 4 refuse.

What this changes in the reading above. It strengthens point 1 (B has no access to the data, and says so). It qualifies
point 4: of the 126 failures, 29 are a format problem, and most of the others come from how the model drives the tool (hand
stepping, bookkeeping across calls, giving up on a timeout), not from the orbital mechanics. The tool itself has three weak
points that the failures expose: a default lunar field (LP165P) that is not the one of the statement, a 30-day bound
announced only by a trailing warning, and a timeout that comes back as an error.

## Limits

One line, 30 instances with 3 attempts each (the 90 episodes of a cell are not independent). The line was designed so that B
fails. The failures were read one by one (above); the reference number used to tell a right answer in a wrong format is the answer of the solved episodes, not the grader's stored value, . The test seeds of this line are private until it is published.

## Reproduce

`python -m orbitbench.harness analyze runs/lunar-test-gptoss-B runs/lunar-test-gptoss-C runs/lunar-test-geminilite-B
runs/lunar-test-geminilite-C runs/lunar-test-qwenflash-B runs/lunar-test-qwenflash-C` (the run folders are not in the
repository; `scripts/run_lunar_test.py` reruns the steps).
