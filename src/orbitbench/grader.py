# src/orbitbench/grader.py
"""Grades a model reply: a labelled outcome and a reward between 0 and 1. No LLM judge, and no look at the transcript."""
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from orbitbench.answer import AnswerError, FinalAnswer, extract_answer
from orbitbench.families import FAMILIES
from orbitbench.families.base import Instance
from orbitbench.replay import Replay, replay

# Frozen on the pilot (docs/freeze.md): the scale of the delta-v gap that halves the reward.
REWARD_SCALE_M_S = 10.0


class Outcome(str, Enum):
    SOLVED = "solved"
    INVALID_FORMAT = "invalid_format"            # no usable <final_answer>
    WRONG_STATUS = "wrong_status"                # ill_posed on a well-posed instance
    INVALID_PLAN = "invalid_plan"                # refused before replay: order, name, epoch, spec
    RUN_FAILED = "run_failed"                    # GMAT failed, timed out or crashed on the plan
    REPLAY_ERROR = "replay_error"                # the benchmark's own replay is inconsistent: investigate
    CONSTRAINTS_VIOLATED = "constraints_violated"
    VALUES_MISMATCH = "values_mismatch"


@dataclass(frozen=True)
class Grade:
    outcome: Outcome
    reward: float
    detail: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.outcome is Outcome.SOLVED


def quantity(name: str, final: dict, plan_delta_v_m_s: float) -> float:
    """A FinalState field, or one derived from the final state and the plan."""
    if name == "rp_km":
        return final["sma_km"] * (1.0 - final["ecc"])
    if name == "ra_km":
        return final["sma_km"] * (1.0 + final["ecc"])
    if name == "plan_delta_v_m_s":
        return plan_delta_v_m_s
    return final[name]


def check_constraints(instance: Instance, final: dict, plan_delta_v_m_s: float = 0.0) -> list:
    """Each constraint of the family against the replayed final state.

    A constraint is a `max` bound or a `target` within `abs_tol`; `periodic` (360 for an angle) wraps the gap.
    """
    checks = []
    for c in instance.constraints:
        value = quantity(c["quantity"], final, plan_delta_v_m_s)
        if "max" in c:
            met = value <= c["max"]
        else:
            gap = value - c["target"]
            if "periodic" in c:
                gap = (gap + c["periodic"] / 2) % c["periodic"] - c["periodic"] / 2
            met = abs(gap) <= c["abs_tol"]
        checks.append({**c, "value": value, "met": met})
    return checks


def reward(met_fraction: float, gap_m_s: float) -> float:
    """Constraints met, discounted by how far the plan's delta-v is above the optimum."""
    return met_fraction / (1.0 + max(0.0, gap_m_s) / REWARD_SCALE_M_S)


def _grade_values(instance: Instance, answer: FinalAnswer) -> Grade:
    family = FAMILIES[instance.family]
    missing = [k for k in instance.tolerances if k not in answer.values]
    if missing:
        return Grade(Outcome.INVALID_FORMAT, 0.0, {"missing": [f"values.{k}" for k in missing]})
    exact = family.reference_values(instance)
    errors = {k: answer.values[k] - exact[k] for k in instance.tolerances}
    solved = all(abs(errors[k]) <= tol for k, tol in instance.tolerances.items())
    return Grade(Outcome.SOLVED if solved else Outcome.VALUES_MISMATCH, 1.0 if solved else 0.0,
                 {"errors": errors})


def _grade_plan(instance: Instance, answer: FinalAnswer, played: Replay) -> Grade:
    detail = {"status": played.status, "reason": played.reason, "plan_delta_v_m_s": played.plan_delta_v_m_s}
    if not played.ok:
        outcome = {"invalid_plan": Outcome.INVALID_PLAN, "epoch_mismatch": Outcome.REPLAY_ERROR}.get(
            played.status, Outcome.RUN_FAILED)
        return Grade(outcome, 0.0, detail)
    family = FAMILIES[instance.family]
    checks = check_constraints(instance, played.final, played.plan_delta_v_m_s)
    optimum = family.reference_delta_v_m_s(instance)
    gap = 0.0 if optimum is None else played.plan_delta_v_m_s - optimum
    score = reward(sum(c["met"] for c in checks) / len(checks), gap)
    detail.update(checks=checks, gap_m_s=gap)
    if not all(c["met"] for c in checks):
        return Grade(Outcome.CONSTRAINTS_VIOLATED, score, detail)
    declared = answer.values.get("delta_v_total_m_s")
    tol = instance.tolerances.get("delta_v_total_m_s")
    if declared is not None and tol is not None and abs(declared - played.plan_delta_v_m_s) > tol:
        detail["declared_delta_v_m_s"] = declared
        return Grade(Outcome.VALUES_MISMATCH, score, detail)
    return Grade(Outcome.SOLVED, score, detail)


def grade(instance: Instance, reply: str, job_dir: Optional[Path] = None, *,
          replay_fn: Callable[..., Replay] = replay) -> Grade:
    """Grades one reply. A maneuver plan is replayed in `job_dir` (new or empty); `replay_fn` lets tests avoid GMAT."""
    try:
        answer = extract_answer(reply)
    except AnswerError as exc:
        return Grade(Outcome.INVALID_FORMAT, 0.0, {"label": exc.label, "message": str(exc)[:300]})
    if answer.status != "solved":
        return Grade(Outcome.WRONG_STATUS, 0.0, {"reason": answer.reason})
    if instance.mode == "values":
        return _grade_values(instance, answer)
    if instance.mode == "orbit" and "inc_deg" not in (answer.initial_orbit or {}):
        return Grade(Outcome.INVALID_FORMAT, 0.0, {"missing": ["initial_orbit.inc_deg"]})
    if job_dir is not None:
        return _grade_plan(instance, answer, replay_fn(instance, answer, job_dir))
    with tempfile.TemporaryDirectory(prefix="orbitbench_") as tmp:
        return _grade_plan(instance, answer, replay_fn(instance, answer, Path(tmp) / "job"))
