# src/orbitbench/families/__init__.py
"""The task families, by name."""
from orbitbench.families.base import Family, Instance
from orbitbench.families.hohmann import HohmannFamily
from orbitbench.families.j2_drift import J2DriftFamily
from orbitbench.families.plane_change_dv import PlaneChangeDvFamily
from orbitbench.families.state_at_date import StateAtDateFamily
from orbitbench.families.tle_state import TleStateFamily

FAMILIES = {family.name: family for family in (HohmannFamily(), PlaneChangeDvFamily(), StateAtDateFamily(),
                                                       TleStateFamily(), J2DriftFamily())}


def generate(family: str, seed: int, mode: str) -> Instance:
    return FAMILIES[family].generate(seed, mode)


__all__ = ["FAMILIES", "Family", "Instance", "generate"]
