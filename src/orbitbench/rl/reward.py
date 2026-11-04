# src/orbitbench/rl/reward.py
"""The reward of a completion: the benchmark grader's, unchanged. No bonus is added to it."""
from orbitbench.answer import AnswerError, extract_answer
from orbitbench.families.base import Instance
from orbitbench.grader import grade


def reward_of(instance: Instance, completion: str) -> float:
    """1.0 if the grader says solved (a correct number, or 'ill_posed' on a trap), else the grader's reward (0.0 for
    a wrong number, a missed trap or a reply that is not a valid answer). Value families have no replay, so no GMAT."""
    return float(grade(instance, completion).reward)


def format_ok(completion: str) -> bool:
    """Whether the last <final_answer> block parses against the answer schema (the content is not checked)."""
    try:
        extract_answer(completion)
    except AnswerError:
        return False
    return True
