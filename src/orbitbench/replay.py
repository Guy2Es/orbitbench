# src/orbitbench/replay.py
"""Replays a maneuver plan in GMAT through gmat-mcp's runner, from the state the instance imposes.

GMAT does not reject a stop epoch that is not after the current epoch: it runs to its 30-day bound and the
job still reports ok. So the plan is checked here, never emitted as a `propagate` to a date that is not
strictly later, and the final state must carry the instance's final epoch.
"""
import math
from dataclasses import dataclass
from typing import Optional

from orbitbench import gmat_mcp
from orbitbench.answer import FinalAnswer
from orbitbench.constants import ACCURACY, INTEGRATOR
from orbitbench.epoch import format_epoch, parse_epoch
from orbitbench.families.base import Instance

MAX_MANEUVERS = 10
EPOCH_TOLERANCE_MS = 1
PROPAGATOR, FORCE_MODEL = "Prop", "FM"


class PlanError(ValueError):
    """A plan the grader refuses to replay: ordering, spacecraft name, epochs, spec rejection."""


@dataclass(frozen=True)
class Replay:
    ok: bool
    status: str                     # ok | invalid_plan | failed | timeout | crashed | epoch_mismatch
    reason: Optional[str]
    final: Optional[dict]           # FinalState as a dict, keyed by field
    plan_delta_v_m_s: float
    duration_s: float = 0.0


def plan_delta_v_m_s(answer: FinalAnswer) -> float:
    """Sum of the burn norms, in m/s."""
    return 1000.0 * sum(math.sqrt(sum(c * c for c in m.delta_v_km_s)) for m in answer.maneuvers)


def _propagate(epoch_ms: int) -> dict:
    return {"type": "propagate", "propagator": PROPAGATOR, "spacecraft": ["Sat"],
            "stop": {"type": "epoch", "epoch": format_epoch(epoch_ms)}}


def build_mission(instance: Instance, answer: FinalAnswer) -> dict:
    """The Mission Spec that flies the plan. Raises PlanError for a plan that cannot be replayed."""
    if len(answer.maneuvers) > MAX_MANEUVERS:
        raise PlanError(f"more than {MAX_MANEUVERS} maneuvers")
    start, end = parse_epoch(instance.epoch), parse_epoch(instance.final_epoch)
    sequence, current = [], start
    for i, m in enumerate(answer.maneuvers, start=1):
        if m.spacecraft != instance.satellite:
            raise PlanError(f"maneuver {i}: the spacecraft is {instance.satellite!r}, not {m.spacecraft!r}")
        try:
            when = parse_epoch(m.epoch_utc)
        except ValueError as exc:
            raise PlanError(f"maneuver {i}: {exc}") from None
        if when < current:
            raise PlanError(f"maneuver {i} is dated before {'the previous one' if i > 1 else 'the initial epoch'}")
        if when > end:
            raise PlanError(f"maneuver {i} is dated after the final epoch")
        if when > current:   # never to a date that is not strictly later: GMAT would run to its 30-day bound
            sequence.append(_propagate(when))
            current = when
        sequence.append({"type": "impulsive_burn", "name": f"M{i}", "spacecraft": instance.satellite,
                         "frame": m.frame, "delta_v_km_s": list(m.delta_v_km_s)})
    if end > current:
        sequence.append(_propagate(end))
    return {"spec_version": "1", "name": f"{instance.family}_{instance.seed}", "central_body": "Earth",
            "epoch": instance.epoch,
            "spacecraft": [{"name": instance.satellite, "state": instance.initial_state}],
            "force_models": [{"name": FORCE_MODEL, **({"gravity": instance.gravity} if instance.gravity else {})}],
            "propagators": [{"name": PROPAGATOR, "force_model": FORCE_MODEL, "integrator": INTEGRATOR,
                             "accuracy": ACCURACY}],
            "sequence": sequence}


def replay(instance: Instance, answer: FinalAnswer, job_dir, *, timeout_s: float = 300.0, backend=None) -> Replay:
    """Flies the plan in GMAT. `job_dir` must be new or empty."""
    plan_dv = plan_delta_v_m_s(answer)
    if not gmat_mcp.add_to_path():
        raise RuntimeError(f"gmat-mcp checkout not found: set {gmat_mcp.ENV_VAR} (looked in {gmat_mcp.checkout_path()})")
    from core.runner import run_mission
    from core.spec import load_mission
    try:
        mission = load_mission(build_mission(instance, answer))
    except (PlanError, ValueError) as exc:   # pydantic's ValidationError is a ValueError
        return Replay(False, "invalid_plan", str(exc)[:500], None, plan_dv)
    run = run_mission(mission, job_dir, timeout_s=timeout_s, backend=backend)
    if not run.run.ok:
        return Replay(False, run.run.status.value, run.run.reason, None, plan_dv, run.run.duration_s)
    final = run.results.final[instance.satellite].model_dump()
    gap_ms = abs(parse_epoch(final["epoch_utc"]) - parse_epoch(instance.final_epoch))
    if gap_ms > EPOCH_TOLERANCE_MS:
        return Replay(False, "epoch_mismatch", f"the replay ended on {final['epoch_utc']}, not on "
                      f"{instance.final_epoch}", final, plan_dv, run.run.duration_s)
    return Replay(True, "ok", None, final, plan_dv, run.run.duration_s)
