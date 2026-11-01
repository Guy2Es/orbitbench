# src/orbitbench/answer.py
"""The <final_answer> JSON every condition returns, and its extraction from a model reply."""
import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from orbitbench.epoch import EPOCH_PATTERN

_BLOCK = re.compile(r"<final_answer>(.*?)</final_answer>", re.DOTALL)


class AnswerError(ValueError):
    """The reply has no usable answer. `label` says why; it is a labelled failure, never a retry."""

    def __init__(self, label: str, message: str):
        super().__init__(message)
        self.label = label


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Maneuver(_Strict):
    epoch_utc: str
    spacecraft: str
    frame: Literal["VNB", "LVLH", "MJ2000Eq", "Inertial"]
    delta_v_km_s: list[float] = Field(min_length=3, max_length=3)

    @field_validator("epoch_utc")
    @classmethod
    def _epoch_format(cls, value: str) -> str:
        if not re.fullmatch(EPOCH_PATTERN, value):
            raise ValueError("epoch_utc must look like '01 Jan 2026 00:00:00.000'")
        return value


class Claims(_Strict):
    verified: bool
    method: Optional[str] = None


class FinalAnswer(_Strict):
    schema_version: Literal["1.0"]
    status: Literal["solved", "ill_posed"]
    values: dict[str, float] = Field(default_factory=dict)
    initial_orbit: Optional[dict] = None
    maneuvers: list[Maneuver] = Field(default_factory=list)
    reason: Optional[str] = None
    claims: Optional[Claims] = None


def extract_answer(reply: str) -> FinalAnswer:
    """The last <final_answer> block of a reply, parsed. Strict JSON: no code fence, no comment."""
    blocks = _BLOCK.findall(reply)
    if not blocks:
        raise AnswerError("no_final_answer", "the reply has no <final_answer> block")
    try:
        data = json.loads(blocks[-1])
    except json.JSONDecodeError as exc:
        raise AnswerError("not_json", f"the block is not valid JSON: {exc}") from None
    try:
        return FinalAnswer.model_validate(data)
    except ValidationError as exc:
        raise AnswerError("schema", f"the JSON does not match the answer schema: {exc}") from None


def render_reply(answer: FinalAnswer) -> str:
    """A reply that carries `answer`: for tests and reference solutions."""
    return f"<final_answer>{answer.model_dump_json()}</final_answer>"
