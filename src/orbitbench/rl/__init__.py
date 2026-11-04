# src/orbitbench/rl/__init__.py
"""What the RL training of a small model needs from the benchmark: training instances, a reward, the benchmark prompt.

Nothing here runs a trainer. The trainer (TRL or Unsloth, on a rented or Colab GPU) imports these functions."""
from orbitbench.rl.data import TRAIN_FIRST_SEED, TRAIN_SCHEDULE, chat_of, train_instances
from orbitbench.rl.reward import format_ok, reward_of

__all__ = ["TRAIN_FIRST_SEED", "TRAIN_SCHEDULE", "chat_of", "format_ok", "reward_of", "train_instances"]
