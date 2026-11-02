# tests/test_gmat_j2_drift.py
"""The j2_drift reference compared with GMAT's JGM3 degree-2 order-0 propagation of the same elements."""
import math

import pytest

from orbitbench.answer import FinalAnswer
from orbitbench.families import FAMILIES, generate
from orbitbench.replay import replay

pytestmark = pytest.mark.gmat


@pytest.mark.parametrize("seed", range(5))
def test_the_reference_matches_gmat_far_inside_the_tolerance(seed, tmp_path):
    inst = generate("j2_drift", seed, "values")
    ref = FAMILIES["j2_drift"].reference_values(inst)
    played = replay(inst, FinalAnswer(schema_version="1.0", status="solved"), tmp_path / "job")
    assert played.ok, played.reason
    for key, tol in inst.tolerances.items():
        assert abs(math.remainder(played.final[key] - ref[key], 360.0)) < tol / 10


def test_far_from_j2000_the_replay_would_not_match_a_z_axis_reference(tmp_path):
    # Documents why the epoch is fixed near J2000: in 2026 the Earth's axis is tilted by precession.
    import dataclasses
    from orbitbench.epoch import add_seconds
    base = generate("j2_drift", 3, "values")
    late = dataclasses.replace(base, epoch="01 Jan 2026 00:00:00.000",
                               final_epoch=add_seconds("01 Jan 2026 00:00:00.000", base.params["dt_days"] * 86400))
    played = replay(late, FinalAnswer(schema_version="1.0", status="solved"), tmp_path / "job")
    assert played.ok, played.reason
    ref = FAMILIES["j2_drift"].reference_values(base)
    assert abs(math.remainder(played.final["raan_deg"] - ref["raan_deg"], 360.0)) > base.tolerances["raan_deg"] / 10
