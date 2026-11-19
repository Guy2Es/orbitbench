> Status (9 November 2026): this protocol belongs to a separate study, to be reported in a later article. It is not part of the
> v1.0 report, which trains no model. It is kept unchanged below, with the preregistration of H6 and question 1.
>
> Amended on 12 November 2026, before any training run: the amendment at the end of this file changes the condition, the
> method and the budget. Where the two texts differ, the amendment applies. The text of 4 November is kept as written.
>
> Amended twice on 16 November 2026, before any training run: first for the move of the rollouts and fine-tunes to Colab,
> then to fix the model, make some rules exact and record the commitment of the private test range. A later amendment
> applies where it differs from an earlier one.

# RL training of a small open model: protocol (written before the first training run)

Question: does a small open model improve on OrbitBench after reinforcement learning on analytical families, and does the
gain reach families it never saw? The result is published as measured, with no gain if there is none.

## Model and arms

- Model: Qwen3-4B-Instruct-2507, served for evaluation through Ollama with a 16k context. Same weights before and after.
- Starting point (audit of 4 Nov 2026, development seeds, 84 episodes): 6 solved; 30 of the 84 replies fail only on a missing
  `schema_version`. Mean reward is near zero, so a plain RL start would see almost no signal.
- Three arms, compared on the same instances:
  0. **Baseline**: the model as it is.
  1. **Format control**: a short SFT on the model's own replies that parse against the answer schema (self-distillation:
     the answers are the model's, right or wrong; no reference solution is ever shown). It measures what the format alone is worth.
  2. **RL**: the format-control model, then GRPO with the reward below.
- The gain of arm 2 over arm 1 is what the reinforcement learning added; the gain of arm 1 over arm 0 is the format.

## Training data and reward

- Instances come from `orbitbench.rl.train_instances`: hohmann (values), plane_change_dv (values), tsiolkovsky, escape_velocity,
  plus the three traps and their twins as a fixed share (6 of 18 slots), so that answering `ill_posed` every time cannot pay.
- Seeds start at 1,000,000. Development seeds are 0 to 9 and the test range stays below 1,000,000 (checked by hand when the
  range is drawn: it is not in the repository). No training statement equals a development statement (tested).
- Reward: `orbitbench.rl.reward_of`, which is the benchmark grader's reward unchanged. No separate format bonus.
- Prompt: `orbitbench.rl.chat_of`, the benchmark's system prompt for condition A plus the statement. Single turn, no tool, no GMAT.

## Held out, fixed here before any training

- Families never used in training or in any data of the arms: `hohmann_or_bielliptic_plan` and `plane_change_budget_plan`
  (maneuver plans, level 3, replayed in GMAT at evaluation only).
- Also reported: condition A and B on levels 1 and 2 of the v1.0 benchmark, and the trap lines.

## Evaluation

- Same instances, same prompt, same limits for the three arms; at least 3 training seeds for arm 2; k = 3 attempts per instance.
- Metrics: strict solve rate (format included), solve rate among replies that parse, trap detection and false-trap rate.
- Paired bootstrap on the difference per instance. Development seeds during the work; the test seeds are opened once, at the end.
- Watch: drift toward `ill_posed`, memorized templates (rephrased statements), reply length.

## What does not change

The frozen v1.0 catalog, tolerances, prompts and limits. The training families are outside it.

## Amendment of 12 November 2026 (written before any training run)

The text above is kept as written on 4 November. This amendment records what was measured since, what changes and why, and
the protocol that now applies. No model has been trained and no test seed has been read: every figure below comes from the
untrained model, on development seeds or training seeds.

### 1. What was measured since 4 November

Model for all of it: Qwen3-4B-Instruct-2507 through Ollama, 16k context, untrained.

1. **Condition A costs too many tokens and sits near the floor.** `runs/rl-length` (144 replies: `train_instances(72)`, which
   holds 40 distinct instances (4), 2 attempts each, temperature 1.0, cap of 4,096 tokens): mean 3,299 tokens per reply, 77 of 144 cut at the cap, 53 parse, 18
   solved (hohmann 0/24, plane_change_dv 3/24, tsiolkovsky 5/24, escape_velocity 10/24, the six trap and twin lines 0/48), 77 s
   per reply at 43 tokens per second. The shortest reply has 835 tokens. In A the reward mostly measures arithmetic done by
   hand to 1 m/s on values near 3 km/s. The smoke notebook in `runs/colab` caps completions at 512 tokens, below the shortest
   reply measured: with that cap every reward would be 0 and GRPO would see no signal.
2. **The held-out families cannot be played in A.** `hohmann_or_bielliptic_plan` and `plane_change_budget_plan` are level-3
   maneuver plans; the harness plays only levels 1 and 2 in condition A (`--max-level`, default 2 for A). The text above does
   not say in which condition they are evaluated.
3. **`chat_of` is not the prompt of the benchmark.** The harness runs Inspect's `react` agent, which appends its own default
   paragraph (577 characters: "You are a helpful assistant… You have several tools available… Do some reasoning before
   your actions…") to `system_prompt(condition)`. The 15 logs opened across v0.1, v1.0 and the lunar line all carry it,
   condition A included, where it contradicts "You have no tools". The text is the same for every model, so comparisons
   between models hold; `docs/freeze.md` does not mention it. A model trained on `chat_of` would be trained on a prompt the
   benchmark never sends.
4. **`train_instances` repeats instances.** The seed is `first_seed + i // 18`, so the three slots of a cycle that hold the
   same family share a seed and give the same instance: `train_instances(36)` holds 20 distinct instances, not 36.
5. **Arm 2 of the text above is confounded.** It is the format-control model plus GRPO, so "arm 2 minus arm 1" contains extra
   gradient steps and another algorithm, not only the reward signal.
6. **The format failure is almost one field.** Regrading the 84 replies of the audit (`runs/qwen3-4b-A`, `-B`, `-C`): 49
   parse; 29 fail only because `schema_version` is missing (the text above says 30); 1 fails on another schema error; 4
   carry no `<final_answer>` tag; 1 is not valid JSON. Of the 29, 16 can be graded without GMAT: with the field added, 7 of
   them are solved, all trap detections (`trap_isp`, `trap_period`); the other 13 are maneuver plans, not replayed. So the
   traps carry signal once the format is learned. In B, 13 of the 34 episodes never call Python.
7. **Time and tokens per episode in B** (the audit, 34 episodes): mean 96 s and 3,892 output tokens; 114 s for the 4
   held-out-plan episodes, 57 s for the 6 hohmann and plane_change_dv episodes, 32 s for the 6 trap episodes. Counting
   input, cache-read and output tokens, 7 of the 34 episodes exceed 20,000 tokens, 2 exceed 40,000, none exceeds 60,000.
8. **Test seeds.** The ranges of v0.1, v1.0 and the lunar line are published and spent (`docs/test_seeds.md`); this study
   needs a range of its own. With two held-out families, the bootstrap of `analysis.py` (families, then instances) has two
   clusters and is degenerate; the bootstrap here is over instances.

### 2. What changes, and why

- **Condition: A becomes B** (Python in the sandbox, no GMAT) for training and for the main evaluation. Reasons: 1, 2 and 6.
- **Method: GRPO becomes reward-filtered self-training**: the model plays, the grader's reward selects replies, the model is
  fine-tuned on the kept replies, and the loop repeats (the family of ReST-EM and rejection-sampling fine-tuning). Reasons:
  an episode in B takes one to two minutes on the GTX 1070 (7); GRPO needs the rollouts and the gradient on one GPU, the
  free Colab T4 has session limits that are not published, and the GTX 1070 (compute capability 6.1) is not supported by
  the current PyTorch builds for training. Here the rollouts run at home through the real harness and Colab runs only short
  fine-tunes that can be restarted.
- **Arms 1 and 2 are matched** (same loop, same data volume, same steps), so that arm 2 minus arm 1 is the reward signal
  alone (5).
- **The model is chosen by a rule fixed here** (phase 0 below), not by preference. The worry about tokens and about the JSON
  format is a measurable question, and the format failure of Qwen3-4B is one missing field (6).
- **The held-out families are evaluated in B**, not in A (2).
- **The test range is new and private** (8).

### 3. The protocol

**Phase 0: choice of the model** (training seeds only, a block of 1,900,000 and above, kept apart from the training blocks).
Candidates: Qwen3-4B-Instruct-2507 (the current one), Qwen3.5-4B, Qwen3.5-2B and Gemma 4 E2B, in Q4_K_M through Ollama, 16k
context, thinking switched off on the server side. Each plays 36 distinct training instances twice in condition B (72
episodes) through the harness, with the spending guard below. A candidate is eligible if: tool calls work through the
unchanged harness; its replies carry no thinking block; a LoRA fine-tune and a GGUF export work on a free Colab T4; and at
least one episode is solved in three of the four number families. Among the eligible candidates the model with the most
solved episodes per GPU-hour is kept. If none is eligible, Qwen3-4B-Instruct-2507 is kept. The table and the choice are
added to this file, dated, before any training. If the chosen model's mean time per episode in phase 0 exceeds 90 s, the
blocks below are 96 instances × 4 attempts instead of 144 × 4, and nothing else changes.

**Arms, all in condition B, all served as a GGUF made by the same export.**
0. Baseline: the model as exported, no adapter.
1. Format control: self-training on the model's own replies that parse, right or wrong.
2. Reward: self-training on the model's own replies that the grader rewards (reward 1.0, the grader unchanged, no bonus).

Arms 1 and 2 share everything else: the same instances, the same loop, the same number of kept examples and of optimizer
steps. Arm 2 minus arm 1 is what the reward signal adds; arm 1 minus arm 0 is what the format is worth.

**Loop, for each training seed t = 0, 1, 2 (two rounds, fixed now).**
- Rollouts go through the harness: the prompt as it is really sent (3), its Python tool, its 60-message limit, and a spending
  guard of 60,000 tokens per episode (`--token-limit`, input, cache-read and output tokens counted; see 7).
- Blocks are sets of 144 distinct training instances in the mix of the text above, with no instance in two blocks. Each
  training seed has its own round-0 block and its own round-1 block; both arms play the same blocks.
- Round 0: the base model plays the round-0 block, 4 attempts per instance. Kept for arm 2: replies with reward 1.0, at most
  2 per instance, the shortest first. Kept for arm 1: replies that parse, at most 2 per instance, drawn at random down to the
  same count. The base model is fine-tuned on each set. Minimum: 48 rewarded replies; if round 0 keeps fewer, another
  round-0 block is played, at most twice, and the kept sets are pooled.
- Round 1: each arm's round-0 model plays the round-1 block, 4 attempts per instance; same selection; the base model is
  fine-tuned again, **from the base**, on the kept replies of rounds 0 and 1.
- Fine-tune: LoRA r = 16, learning rate 2e-4, 3 epochs, loss on the assistant turns only, seed t. Identical for both arms; no
  setting is tuned on a result. The examples are the full transcripts as the model saw them, tool turns included.

**Evaluation** (a new private range, drawn by the author before any training and opened once, at the end).
- Condition B, k = 3, same instances and limits for all arms, with the same guard of 60,000 tokens. Three groups:
  in distribution (the 4 number lines, the 3 traps and the 3 twins, 6 seeds each: 60 instances); near transfer
  (`hohmann/maneuvers` and `plane_change_dv/maneuvers`, 10 each; `state_at_date`, `j2_drift` and `tle_state`, 6 each: 38
  instances); held out as declared above (`hohmann_or_bielliptic_plan` and `plane_change_budget_plan`, 20 each: 40 instances).
- **Primary (H6):** arm 2 minus arm 0 on the held-out families, on the grader's reward (it carries the gap to the optimum; 0
  without a valid plan). Paired per instance; the attempts and the training seeds of an instance are averaged first; 95 %
  bootstrap over the instances, per family and pooled. The strict solve rate is shown next to it. H6 is supported if the
  pooled interval lies above zero. The interval is over instances only: the spread across training seeds is shown apart,
  each seed on its own.
- Secondary: arm 2 minus arm 1; arm 1 minus arm 0; strict solve rate; solve rate among replies that parse; trap detection
  and false-trap rate on the twins; output tokens per episode.
- **Floor rule, stated now:** if arms 0 and 2 both solve nothing on the held-out families, H6 is reported as not testable at
  this model size, and the reward difference and the near-transfer lines are the result.
- Exploratory: condition A (levels 1 and 2) and condition C (the held-out lines), k = 1, for arm 0 and the models of
  training seed 0.
- Development seeds 0 to 9 serve only for go/no-go checks of the pipeline. The watch list of the text above stays
  (drift toward `ill_posed`, memorized templates, reply length).

**Budget.** From the audit (7): about 60 s per episode in the training mix (an estimate, to be replaced by phase 0), 96 s
for an evaluation episode. A block of 576 episodes is about 10 h. Each training seed plays 3 blocks (round 0 once, round 1
once per arm): 9 blocks, about 86 h. Evaluation is 414 episodes per model, about 11 h, for 7 models (arm 0; arms 1 and 2
for 3 training seeds): about 77 h. Phase 0 is about 5 h. In all about 170 h on the GTX 1070, four weeks at 6 h a day. Colab:
12 fine-tunes of 20 to 40 minutes, plus one export of the base model, each restartable. A 2B model would take about half.

### 4. To do before the first training run (not done at this date)

- `train_instances` must return distinct instances (4), a trap still sharing its seed with its twin; the test that no
  training statement equals a development statement stays.
- Training rollouts must come from the harness, or `chat_of` must return the system message the harness really sends (3).
- A training suite in the harness; an export of the kept transcripts with a manifest and hashes; the Colab fine-tune and
  GGUF export; a paired comparison between run folders of one condition, bootstrapped over instances (8).
- A check, before the first fine-tune, that the first prompt rendered by the fine-tuning chat template has the token count
  that Ollama recorded. Ollama renders tools with its own template; if the counts differ, the model is served through
  llama.cpp's `llama-server --jinja`.
- If the GGUF export of a 4B model runs out of memory on free Colab: export the LoRA adapter, convert it with llama.cpp's
  `convert_lora_to_gguf.py`, and load it with an Ollama `ADAPTER` line. The base model is exported the same way for arm 0.
- The private test range, drawn and checked against the published ranges of `docs/test_seeds.md`.
- The table of phase 0 and the model chosen, dated, in this file.
- Dated entries in `docs/hypotheses.md` (its rule asks for one when the protocol changes) and in `docs/freeze.md` (3). This
  amendment makes neither.

### 5. What does not change

H6 and question 1 as recorded. The two held-out families. The reward: the grader's, no bonus. Training seeds from 1,000,000.
The frozen v1.0 catalog, tolerances, prompts and limits.

## Amendment of 16 November 2026: rollouts and fine-tunes on Colab (written before any training run)

Nothing is trained and no test seed is read when this is written. The amendment of 12 November applies, except for the points
below. What does not change: H6 and question 1, the reward (the grader's), the arms, the loop (two rounds, three training
seeds), the selection rules, the held-out families, the private test range, the evaluation instances and limits.

**What changes.**
1. **Where training rollouts are played.** On Colab (T4, Colab Pro, the models and data on a Google Drive folder), not on the
   GTX 1070. The harness is the same code, cloned from the repository.
2. **How the model is served there.** By vLLM, from the merged 16-bit model, in fp16, with tool calls parsed by the server
   (`hermes` parser for Qwen3), 16k context, 8 episodes in parallel. The 12 November text said Q4_K_M through Ollama.
3. **Sandbox of those rollouts.** The Python tool runs on the Colab virtual machine (`--sandbox local`, with network access),
   because Colab has no Docker. The prompt, the tool, the 60-message limit, the 60,000-token guard and the grading are
   unchanged; grading of the training families needs no GMAT. This departs from "no network" for training rollouts only.
4. **Fine-tune.** LoRA in 16 bits, not 4-bit QLoRA (`--load-4bit` only if the T4 runs out of memory, and the results then say
   so), so that a merged model is exactly the base plus its adapter and arm 0 is the original weights, downloaded and hashed.
   r = 16, learning rate 2e-4, 3 epochs, loss on assistant turns only: as fixed on 12 November.
5. **Evaluation stays at home**, in Docker, with GMAT replay (the held-out families are plans), served by Ollama from a GGUF
   Q4_K_M made at home from each merged model, the same way for arm 0 and the arms (`scripts/rl_gguf.py`). The model that is
   evaluated (Q4_K_M) is therefore not the one that played the training rollouts (fp16). This is stated here so that it is
   not read as an oversight; arm 0 is evaluated the same way, so the primary comparison is not affected by it.
6. **Phase 0** is played on Colab with vLLM, in fp16. Its figures are not comparable with the audit of 4 November (Q4_K_M,
   Ollama). The eligibility rule reads: tool calls work through the unchanged harness against the vLLM server; no thinking
   block; a LoRA fine-tune and a merged 16-bit save work on a T4; at least one solved episode in three of the four number
   families. A candidate that vLLM cannot serve with tool calls is not eligible. Choice and tie-break as before.
7. **Budget.** The hours of 12 November were for the GTX 1070 without parallelism. On Colab the time per block is measured in
   phase 0, with the compute units it uses (200 units a month on the Colab Pro plan). If the measured units for the 9 blocks
   exceed 150 a month, the blocks are 96 instances x 4 attempts (the rule of 12 November) or the study is spread over two
   months; nothing else changes.

**Consequence for the written results.** The report states: training rollouts fp16 with a local sandbox on Colab; evaluation
Q4_K_M in Docker at home; arm 0 evaluated through the same path as the arms.

**Files.** `scripts/rl_colab.py` (vLLM server, Drive layout), `scripts/rl_round.py` (`--server`, `--sandbox`, `RL_DIR`),
`scripts/rl_finetune.py` (16-bit LoRA, merged output, original weights for arm 0), `scripts/rl_gguf.py` (home conversion).

## Second amendment of 16 November 2026: the model, rules made exact, the private range (written before any training run)

Nothing is trained and no test seed is read when this is written. It follows a check of the two amendments above against
the code, before the first Colab session. Where it differs from them, it applies.

1. **The model is Qwen3-4B-Instruct-2507; there is no bake-off.** The amendment of 12 November planned a choice among four
   candidates by a rule. It is dropped: the three other candidates each need their own tool-call parser on vLLM, a switch
   for their thinking mode and possibly another fine-tuning loader, none of which the author could test, and the format
   failure of Qwen3-4B is one missing field (12 November, 6). Phase 0 remains as a measurement: the base model plays 36
   training instances twice (72 episodes, seeds from 1,900,000) on Colab, to measure the time and the compute units of a
   block. Its table is added to this file, dated, before any training.
2. **Size of the blocks on Colab.** The rule "more than 90 s per episode: blocks of 96 instances" (12 November) was written
   for one episode at a time on the GTX 1070. With 8 episodes in parallel the time of one episode is not comparable with
   it. On Colab the units rule of 16 November (point 7) alone applies. From phase 0, the hours of a block are estimated as
   (sum of the episode times / 8) x 576 / 72, and the units as 9 blocks x these hours x the rate Colab shows for the
   runtime. Above 150 units: blocks of 96 instances x 4 attempts, or the study over two months.
   `scripts/rl_round.py bakeoff --parallel 8 --units-per-hour <rate>` prints the estimate.
3. **Second round-0 block.** "At most twice" (12 November) reads: round 0 is played at most twice in all, the first block
   and one more (`--redraw 1`), pooled. If the two blocks together keep fewer than 48 rewarded replies, the fine-tune runs
   on what there is and the count is reported. (Superseded the same day by the second addendum below: up to 8 blocks.)
4. **Long transcripts.** A reply whose whole transcript exceeds 8,192 tokens (the input and the output of the last model
   call, as the server counted them) is in neither arm's set: the fine-tune cannot hold it in memory. Such replies are
   removed before the "at most 2 per instance" rule and before the sizes are matched, so the two arms keep the same number
   of examples. The fine-tune still reports what it drops; it should be nothing.
5. **The base of the fine-tunes is the files of arm 0.** Arm 0 is `Qwen/Qwen3-4B-Instruct-2507` as downloaded once to the
   Drive folder, with the commit of the repository and the SHA-256 of its weight files in its manifest. Every fine-tune
   loads these files, not another copy of the model, and writes their hashes in its own manifest. The tokenizer and the
   chat template are therefore the ones the server used during the rollouts.
6. **Sampling during rollouts.** The harness sends no sampling setting, as in the benchmark. vLLM then uses the
   `generation_config.json` of the model folder; the fine-tune copies the base model's file into a merged model that lacks
   one, so that every model is sampled the same way. The settings are printed when a server starts and are reported.
7. **Inspect provider.** The harness reaches the server through Inspect's `vllm/` provider. An episode that outgrows the
   16k context ends there (`model_length`) and is graded on what it holds; the generic OpenAI-compatible provider would
   raise an error instead. At home Ollama truncates the prompt and the episode goes on: a difference between the training
   rollouts and the evaluation, the same for every arm.
8. **GPU of the fine-tunes.** Fixed after the smoke test, then the same for the 12 fine-tunes: the T4 if a 16-bit
   fine-tune fits in its memory; otherwise the L4, still in 16 bits; `--load-4bit` only if the L4 fails too, and the
   results then say so (16 November, point 4).
9. **The private test range is drawn.** `scripts/rl_draw_seed.py` drew it on 16 November 2026 and wrote it in `.env`,
   which is not in the repository; it was not displayed. It lies below 1,000,000, at least 1,000 seeds away from the first
   seeds of v0.1 and v1.0. Commitment, the SHA-256 of `orbitbench-rl:<first seed>:<salt>`:
   `37efd68465455e0807cfd36eb7ef9690cea1dcdf1a91c183f55a5fa11d23bf73`. The seed and the salt are published with the results.
10. **Smoke test.** Before phase 0, a smoke test checks the whole chain on Colab: the server, 16 episodes, the token-count
    check, a fine-tune on the few replies that parse, the serving of the merged model. It plays training seeds from
    1,950,000, which belong to no block and not to phase 0. Its model is deleted and counts in no result.

**To do before the first training run, updated.** Done: distinct training instances, the real system message, the training
suite, the export with manifests and hashes, the paired comparison, the private range. Still to do, on Colab: the smoke
test with its token-count check, then phase 0 and its table in this file. At home, before the evaluation: the same
token-count check on a log played through Ollama; if the counts differ, the models are served through `llama-server --jinja`.

**Files.** `notebooks/orbitbench_rl_colab.ipynb` (the Colab cells, in order), `scripts/rl_draw_seed.py`.

**Addendum of 16 November 2026 (smoke test on Colab, before any training run).** Two things the first Colab session showed.
(a) The first prompt rendered by the fine-tuning chat template had 89 tokens fewer than the server counted: the export took a
tool's description from Inspect's log as an `attachment://` reference. The export now takes the tools as the first request
carried them, references resolved; the two counts are then equal (778, 784 and 782 tokens on the smoke episodes), which the
check of `rl_finetune.py` enforces before any fine-tune. (b) Unsloth packs several examples into one row by default, so the
number of optimizer steps would follow the total length of the examples, and the reward arm (shortest replies) would get fewer
steps than the format arm. Packing is switched off: the steps follow the number of examples, as the protocol says. Nothing else
in the fine-tune changes. The fine-tune fits on the T4 in 16 bits (point 8 above: the L4 and 4-bit fallbacks are not used).

**Second addendum of 16 November 2026 (phase 0 on Colab, before any training run).**

*Measured.* Phase 0 on Colab (Qwen3-4B-Instruct-2507, vLLM fp16 on a T4, condition B, 36 instances x 2 epochs = 72 episodes from
seed 1,900,000, 8 in parallel, local sandbox): 13 min 35 s; **1 episode solved of 72 (1.4 %)**: escape_velocity 0/12, hohmann 0/12,
plane_change_dv 1/12, tsiolkovsky 0/12, the six trap and twin lines 0/24; mean 2.0 turns and 999 output tokens per episode.
Estimate by the rule of point 2: about 1.6 h for a block of 144 x 4 episodes and about 23 Colab units for 9 blocks (rate
1.57 units/h), well under 150: **blocks of 144 instances**.

*Cause.* Three transcripts read (hohmann, escape_velocity, tsiolkovsky): the model writes a correct Python computation whose last
line is a bare expression, with no `print`. The Python tool then returns an empty output, and the model states a number it did
not compute (1000.0 m/s; 342.1 kg where the exact value is about 452 kg). The statements and the grader are sound. This is the
behaviour the fine-tuning is meant to change, so the study stands; the tool and the prompts are not changed (frozen benchmark,
arm 0 stays comparable).

*Consequence for the minimum of 48.* At about 1.4 %, a block of 576 episodes keeps about 8 rewarded replies, and one extra block
(point 3 above) would give about 16. **Round-0 rule, replacing point 3 above:** the base model plays round-0 blocks, one after
the other (`--redraw 0, 1, ...`), until the pooled blocks keep 48 rewarded replies (reward 1.0, at most 2 per instance, the
shortest first), **8 blocks at most** per training seed. The format arm is matched in size to the reward arm as before. If 48 is
not reached after 8 blocks, the fine-tune runs on what there is and the count is reported; **under 24 rewarded replies, the study
stops there and reports it as a negative result**. Round 1 is unchanged: one block per arm. Cost: at most 3 x (8 + 2) = 30 blocks of
about 2.5 units, 75 units, plus about 10 for the 12 fine-tunes, against the ceiling of 150. The rewarded replies may come from few
families; that is how the filter works, and the held-out families of the evaluation show what carries over. Nothing else changes.

**Round 0 of training seed 0 (Colab, 17 November 2026, before any fine-tune).** Three blocks of 144 x 4 = 576 episodes were played by
the base model (`--redraw 0, 1, 2`). Solved: 15, 20 and 16 (2.6 %, 3.5 %, 2.8 %); block times 2 h 00, 1 h 57, and 55 min for the
third (its session was cut at 227/576 and the relaunch kept the finished episodes). Pooled by the rule above: **50 rewarded replies
from 45 instances** (71,664 output tokens, sha256 f6d4026de902), so 48 is reached after 3 blocks. The format arm is matched at 50
replies from 49 instances (53,812 tokens, sha256 0403a065ac71). One reply longer than 8192 tokens is left out of the sets.
*Concentration.* Solved over the three blocks, by line: trap_period_twin 20, tsiolkovsky 17, hohmann 6, plane_change_dv 5,
trap_isp_twin 2, trap_radius_twin 1; **escape_velocity, trap_isp, trap_period and trap_radius: 0**. The two largest lines hold
about 73 % of the rewarded replies. The cause of the failures on trap_isp and trap_period/radius is mostly `invalid_format` and
`missed_trap`. This is how the reward filter behaves; the held-out families of the evaluation show what carries over.

**Round 1 of training seed 0 (Colab, 17 November 2026, before the final fine-tunes).** Each round-0 model played one block of
144 x 4 = 576 episodes (block seed of round 1, instances 1008000 and following); these are training-range instances, not the private
test range. *Reward arm* (`t0r0-reward`): **88 solved (15.3 %, stderr 0.020)**, 2 h 02. By line: trap_period_twin 17/32, hohmann 27/96,
tsiolkovsky 26/96, plane_change_dv 10/96, trap_isp_twin 4/32, trap_radius_twin 4/32; **escape_velocity, trap_isp, trap_period and
trap_radius: 0**. *Format arm* (`t0r0-format`): **15 solved (2.6 %, stderr 0.008)**, 2 h 08: tsiolkovsky 9/96, trap_period_twin 4/32,
plane_change_dv 1/96, trap_isp_twin 1/32; hohmann 0/96 and the same four lines at 0. The base model solved 15, 20 and 16 per block
(2.6 to 3.5 %), so the format arm stays at the base level and the gain of the reward arm does not come from format alone. This is
a training-range measure; the verdict is the home evaluation on the private range and the held-out families.
*Selection (D3).* Round 1 gives 76 rewarded replies from 56 instances (90,850 output tokens, sha256 00646e5cdf17) and the format arm
is matched at 76 replies from 67 instances (77,025 tokens, sha256 061d022f852d). Pooled with round 0: **126 examples per arm**
(`t0-r01-reward.jsonl` sha256 a09f1ba9d95c, `t0-r01-format.jsonl` sha256 cfd7383d94b1). The final fine-tunes start from the base model.

**Round 0 of training seed 1 (Colab, 18 November 2026, before any fine-tune).** Three blocks of 144 x 4 = 576 episodes were played by
the base model (`--redraw 0, 1, 2`). Solved: 14 (2.4 %) and 24 (4.2 %) in the first two blocks, about 2 h each; the solved count of
the third block was not recorded here. After two blocks the pool held 37 rewarded replies (under 48), so a third block was played.
Pooled by the rule above: **53 rewarded replies from 46 instances** (101,941 output tokens, sha256 aa9ac4689958), so 48 is reached
after 3 blocks. The format arm is matched at 53 replies from 53 instances (59,351 tokens, sha256 8c9585f57e18). The concentration by
line is not recorded yet for this seed.

**Round 1 of training seed 1 (Colab, 19 November 2026, recorded after the final fine-tunes, from the Drive manifests).** Each round-0
model played one block of 144 x 4 = 576 episodes on training-range instances, not the private test range. *Reward arm*
(`t1r0-reward`): **103 solved (17.9 %, stderr about 0.016)**. By line: plane_change_dv 40/96, hohmann 30/96, trap_period_twin 12/32,
tsiolkovsky 13/96, trap_radius_twin 6/32, trap_isp_twin 2/32; **escape_velocity, trap_isp, trap_period and trap_radius: 0**. The
solved count of the format arm (`t1r0-format`) was not recorded in this file. *Selection.* Reward arm: 93 rewarded replies from 63
instances (119,397 output tokens, sha256 c80dac5440bb); format arm matched at 93 replies from 75 instances (101,025 tokens, sha256
68319dd436d1). Pooled with round 0: **146 examples per arm** (`t1-r01-reward.jsonl` 109 instances, sha256 5b06a734face;
`t1-r01-format.jsonl` 128 instances, sha256 42d29a7ddf50). The final fine-tunes started from the base model (57 steps each, loss about
0.10 to 0.05 for the format arm); models `t1-reward` and `t1-format` are on Drive.
