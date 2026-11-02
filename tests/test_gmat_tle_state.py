# tests/test_gmat_tle_state.py
"""The tle_state reference against gmat-mcp's TLE reader and against GMAT's own reading of the same TLE."""
import dataclasses

import numpy as np
import pytest

from orbitbench.answer import FinalAnswer
from orbitbench.families import FAMILIES, generate
from orbitbench.reference.tle import sgp4_state
from orbitbench.replay import replay

pytestmark = pytest.mark.gmat


@pytest.mark.parametrize("seed", range(5))
def test_the_state_at_the_tle_epoch_matches_the_core_reader(seed):
    from core.astro.tle import tle_state_teme
    p = generate("tle_state", seed, "values").params
    pos, vel = sgp4_state(p["line1"], p["line2"], 0.0)
    core = tle_state_teme(p["line1"], p["line2"])   # computed at the epoch rounded to the millisecond
    assert np.allclose(pos, core["position_km"], atol=0.02)
    assert np.allclose(vel, core["velocity_km_s"], atol=2e-5)


@pytest.mark.parametrize("seed", range(5))
def test_gmat_reads_the_tle_to_the_same_orbit_in_a_rotated_frame(seed, tmp_path):
    # GMAT returns EarthMJ2000Eq and the reference is TEME: only rotation invariants can be compared.
    full = generate("tle_state", seed, "values")
    inst = dataclasses.replace(full, final_epoch=full.epoch)   # no propagation: GMAT only reads the TLE
    played = replay(inst, FinalAnswer(schema_version="1.0", status="solved"), tmp_path / "job")
    assert played.ok, played.reason
    gp, gv = np.array(played.final["position_km"]), np.array(played.final["velocity_km_s"])
    pos, vel = (np.array(c) for c in sgp4_state(inst.params["line1"], inst.params["line2"], 0.0))
    assert np.linalg.norm(gp) == pytest.approx(np.linalg.norm(pos), abs=0.02)
    assert np.linalg.norm(gv) == pytest.approx(np.linalg.norm(vel), abs=2e-5)
    assert np.linalg.norm(np.cross(gp, gv)) == pytest.approx(np.linalg.norm(np.cross(pos, vel)), rel=1e-5)
