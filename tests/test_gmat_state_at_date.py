# tests/test_gmat_state_at_date.py
"""The state_at_date reference compared with GMAT's own propagation of the same elements."""
import numpy as np
import pytest

from orbitbench.answer import FinalAnswer
from orbitbench.families import FAMILIES, generate
from orbitbench.replay import replay

pytestmark = pytest.mark.gmat


def gmat_state(inst, tmp_path):
    played = replay(inst, FinalAnswer(schema_version="1.0", status="solved"), tmp_path / "job")
    assert played.ok, played.reason
    return np.array(played.final["position_km"]), np.array(played.final["velocity_km_s"])


@pytest.mark.parametrize("seed", range(5))
def test_the_reference_matches_gmat_far_inside_the_tolerance(seed, tmp_path):
    inst = generate("state_at_date", seed, "values")
    ref = FAMILIES["state_at_date"].reference_values(inst)
    pos, vel = gmat_state(inst, tmp_path)
    assert np.allclose(pos, [ref["x_km"], ref["y_km"], ref["z_km"]], atol=inst.tolerances["x_km"] / 100)
    assert np.allclose(vel, [ref["vx_km_s"], ref["vy_km_s"], ref["vz_km_s"]], atol=inst.tolerances["vx_km_s"] / 100)
