# tests/test_freeze_v10.py
"""The frozen v1.0 values: every tolerance, the J2 epochs, the reward, the declared limits, the three prompts, the counts,
and the dataset (the full default instances of the 85 + 9 twins + 3 canaries, then the statements of the development
seeds 0 to 9). The v0.1 values stay in test_freeze.py. A change here changes what the benchmark measures: update
docs/freeze.md and FROZEN together, on purpose."""
import hashlib
import json
from pathlib import Path

import yaml

from orbitbench import grader
from orbitbench.families import generate
from orbitbench.harness import task
from orbitbench.harness.catalog import CANARY_LINES, TWIN_LINES, V10_LINES, instances
from orbitbench.harness.prompt import system_prompt

TEMPLATES = Path(grader.__file__).parent / "families" / "templates"
TRAINING_ONLY = ("tsiolkovsky", "escape_velocity")     # the RL training families: not part of the benchmark, not frozen here


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def live() -> dict:
    default = instances(V10_LINES) + instances(TWIN_LINES) + instances(CANARY_LINES)
    dev = [generate(family, seed, mode) for family, mode, _ in V10_LINES for seed in range(10)]
    return {
        "tolerances": {p.stem: load(p)["tolerance"] for p in sorted(TEMPLATES.glob("*.yaml")) if "tolerance" in load(p) and p.stem not in TRAINING_ONLY},
        "epochs": {p.stem: load(p)["epoch"] for p in sorted(TEMPLATES.glob("*.yaml"))
                   if p.stem in ("j2_drift", "sun_synchronous")},
        "reward_scale_m_s": grader.REWARD_SCALE_M_S,
        "limits": {"message": task.MESSAGE_LIMIT, "python_timeout_s": task.PYTHON_TIMEOUT_S,
                   "gmat_wait_s": task.GMAT_WAIT_S, "gmat_run_timeout_s": task.GMAT_RUN_TIMEOUT_S,
                   "gmat_call_timeout_s": task.GMAT_CALL_TIMEOUT_S},
        "prompts": {c: digest(system_prompt(c)) for c in ("A", "B", "C")},
        "counts": {"v10": len(instances(V10_LINES)), "twins": len(instances(TWIN_LINES)),
                   "canaries": len(instances(CANARY_LINES))},
        "dataset": digest(json.dumps([i.to_dict() for i in default], sort_keys=True)),
        "dev_statements": digest(chr(10).join(i.statement for i in dev)),
    }


FROZEN = json.loads(r"""{
 "counts": {
  "canaries": 3,
  "twins": 9,
  "v10": 85
 },
 "dataset": "4ecbff96fcd3a65f",
 "dev_statements": "a4504016515b7092",
 "epochs": {
  "j2_drift": "01 Jan 2000 12:00:00.000",
  "sun_synchronous": "01 Jan 2000 12:00:00.000"
 },
 "limits": {
  "gmat_call_timeout_s": 180,
  "gmat_run_timeout_s": 300,
  "gmat_wait_s": 45,
  "message": 60,
  "python_timeout_s": 60
 },
 "prompts": {
  "A": "7619113229975d59",
  "B": "b2be00e36d48a2e3",
  "C": "bdfd024bed3245fa"
 },
 "reward_scale_m_s": 10.0,
 "tolerances": {
  "canary": {
   "relative": 0.001
  },
  "circularize_plan": {
   "ecc_max": 0.001,
   "inc_deg": 0.001
  },
  "finite_burn_raise": {
   "inc_deg": 0.001,
   "radius_rel": 0.01
  },
  "frame_trap": {
   "apsis_rel": 0.001,
   "inc_deg": 0.001
  },
  "guess_trap_transfer": {
   "ecc_max": 0.001,
   "inc_deg": 0.001,
   "sma_rel": 0.001
  },
  "hohmann": {
   "delta_v_total_m_s": 1.0,
   "ecc_max": 0.001,
   "inc_deg": 0.001,
   "sma_rel": 0.001
  },
  "hohmann_or_bielliptic_plan": {
   "ecc_max": 0.001,
   "inc_deg": 0.001,
   "sma_rel": 0.001
  },
  "j2_drift": {
   "angle_deg": 0.02
  },
  "plane_change_budget_plan": {
   "ecc_max": 0.001,
   "inc_deg": 0.001,
   "sma_rel": 0.001
  },
  "plane_change_dv": {
   "delta_v_total_m_s": 1.0,
   "ecc_max": 0.001,
   "inc_deg": 0.001,
   "sma_rel": 0.001
  },
  "rendezvous_phasing": {
   "position_km": 2.0,
   "velocity_m_s": 2.0
  },
  "state_at_date": {
   "position_km": 1.0,
   "velocity_km_s": 0.001
  },
  "sun_synchronous": {
   "drift_deg_day": 0.001
  },
  "tle_state": {
   "position_km": 1.0,
   "velocity_km_s": 0.001
  }
 }
}""")


def test_the_frozen_v10_values_have_not_changed():
    assert live() == FROZEN


def test_the_prompts_of_b_and_c_are_those_of_the_v01():
    assert FROZEN["prompts"]["B"] == "b2be00e36d48a2e3" and FROZEN["prompts"]["C"] == "bdfd024bed3245fa"
