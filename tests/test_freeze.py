# tests/test_freeze.py
"""The frozen v0.1 values: tolerances, reward, declared limits, prompts and the statements of the dev seeds.
A change here changes what the benchmark measures: update docs/freeze.md and FROZEN together, on purpose."""
import hashlib
import json
from pathlib import Path

import yaml

from orbitbench import grader
from orbitbench.families import FAMILIES
from orbitbench.harness import task
from orbitbench.harness.catalog import instances
from orbitbench.harness.prompt import system_prompt

TEMPLATES = Path(grader.__file__).parent / "families" / "templates"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def live() -> dict:
    return {
        "tolerances": {p.stem: yaml.safe_load(p.read_text(encoding="utf-8"))["tolerance"]
                       for p in sorted(TEMPLATES.glob("*.yaml"))},
        "reward_scale_m_s": grader.REWARD_SCALE_M_S,
        "reward_samples": [round(grader.reward(f, g), 6) for f, g in ((1.0, 0.0), (1.0, 10.0), (0.5, 0.0), (1.0, -3.0))],
        "limits": {"message": task.MESSAGE_LIMIT, "python_timeout_s": task.PYTHON_TIMEOUT_S,
                   "gmat_wait_s": task.GMAT_WAIT_S, "gmat_run_timeout_s": task.GMAT_RUN_TIMEOUT_S,
                   "gmat_call_timeout_s": task.GMAT_CALL_TIMEOUT_S},
        "prompts": {c: digest(system_prompt(c)) for c in ("B", "C")},
        "statements": digest("\n".join(i.statement for i in instances())),
    }


FROZEN = json.loads(r"""{
 "limits": {
  "gmat_call_timeout_s": 180,
  "gmat_run_timeout_s": 300,
  "gmat_wait_s": 45,
  "message": 60,
  "python_timeout_s": 60
 },
 "prompts": {
  "B": "b2be00e36d48a2e3",
  "C": "bdfd024bed3245fa"
 },
 "reward_samples": [
  1.0,
  0.5,
  0.5,
  1.0
 ],
 "reward_scale_m_s": 10.0,
 "statements": "ec23dfcd40c0a467",
 "tolerances": {
  "circularize_plan": {
   "ecc_max": 0.001,
   "inc_deg": 0.001
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
  "state_at_date": {
   "position_km": 1.0,
   "velocity_km_s": 0.001
  },
  "tle_state": {
   "position_km": 1.0,
   "velocity_km_s": 0.001
  }
 }
}""")


def test_the_frozen_values_have_not_changed():
    assert live() == FROZEN


def test_every_family_has_a_frozen_tolerance_block():
    assert set(FROZEN["tolerances"]) == set(FAMILIES)
