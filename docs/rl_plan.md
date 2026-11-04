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
