# src/orbitbench/families/base.py
"""What every task family provides: an instance from a seed, its statement, and a reference answer."""
import json
from dataclasses import asdict, dataclass, field
from importlib import resources
from typing import Optional

import yaml

from orbitbench.answer import FinalAnswer

MODES = ("values", "maneuvers")


@dataclass(frozen=True)
class Instance:
    """One task. `statement` is all the model sees; the other fields are for the grader."""
    family: str
    mode: str                     # "values" (level 1 or 2), "maneuvers" (level 3) or "orbit" (an orbit to design)
    seed: int
    level: int
    statement: str
    epoch: str
    final_epoch: str
    satellite: str
    initial_state: dict           # a Mission Spec keplerian or cartesian state
    constraints: list = field(default_factory=list)   # checked on the replayed final state
    tolerances: dict = field(default_factory=dict)   # values mode: absolute tolerance per answer field
    params: dict = field(default_factory=dict)
    gravity: dict = field(default_factory=dict)      # Mission Spec gravity of the replay; {} is a point mass
    propulsion: dict = field(default_factory=dict)   # dry mass, tank and thruster, for a plan that uses finite burns
    well_posed: bool = True       # False: the statement cannot be answered as written, and ill_posed is the right answer

    @classmethod
    def from_dict(cls, data: dict) -> "Instance":
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


def load_template(name: str) -> dict:
    text = resources.files("orbitbench.families").joinpath("templates", f"{name}.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def fill(template: str, fields: dict) -> str:
    """A statement paragraph group: the YAML folds paragraph breaks into single newlines, so restore them."""
    return template.format(**fields).replace("\n", "\n\n")


def answer_format(mode: str, satellite: str, keys: tuple = ("delta_v_total_m_s",)) -> str:
    """The reply format, identical in every condition. `keys` are the fields of `values` in values mode."""
    if mode == "values":
        shape = ", ".join(f'"{k}": 0.0' for k in keys)
        body = '{"schema_version": "1.0", "status": "solved", "values": {' + shape + '}}'
    elif mode == "orbit":
        shape = ", ".join(f'"{k}": 0.0' for k in keys)
        body = '{"schema_version": "1.0", "status": "solved", "initial_orbit": {' + shape + '}}'
    else:
        body = ('{"schema_version": "1.0", "status": "solved", "maneuvers": [{"epoch_utc": '
                f'"01 Jan 2026 00:00:00.000", "spacecraft": "{satellite}", "frame": "VNB", '
                '"delta_v_km_s": [0.0, 0.0, 0.0]}]}')
    return ("End your reply with exactly one block <final_answer>...</final_answer> that holds a single JSON "
            "object. Optional fields: reason (why, if status is 'ill_posed'), claims "
            '({"verified": true or false, "method": "..."}) to say whether and how you checked your answer. '
            f"Example of the shape:\n<final_answer>{body}</final_answer>")


def finite_answer_format(satellite: str) -> str:
    """The reply format of a plan of finite burns."""
    body = ('{"schema_version": "1.0", "status": "solved", "finite_burns": [{"epoch_utc": '
            f'"01 Jan 2026 00:00:00.000", "spacecraft": "{satellite}", "duration_s": 0.0, "direction": "prograde"}}]}}')
    return ("End your reply with exactly one block <final_answer>...</final_answer> that holds a single JSON "
            "object. Optional fields: reason (why, if status is 'ill_posed'), claims "
            '({"verified": true or false, "method": "..."}) to say whether and how you checked your answer. '
            f"Example of the shape:\n<final_answer>{body}</final_answer>")


class Family:
    """A task family: a template plus a generator and a reference solution."""
    name: str = ""

    def generate(self, seed: int, mode: str) -> Instance:
        raise NotImplementedError

    def reference(self, instance: Instance) -> FinalAnswer:
        """A correct answer, computed without gmat-mcp's `core`."""
        raise NotImplementedError

    def reference_values(self, instance: Instance) -> dict:
        """The exact value of every field of `instance.tolerances`, in values mode."""
        raise NotImplementedError

    def reference_delta_v_m_s(self, instance: Instance) -> Optional[float]:
        """The optimum the reward measures the gap to, when the family has one."""
        return None


def dump_instance(instance: Instance) -> str:
    return json.dumps(instance.to_dict(), indent=2)
