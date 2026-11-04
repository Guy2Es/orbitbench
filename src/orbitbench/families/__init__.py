# src/orbitbench/families/__init__.py
"""The task families, by name."""
from orbitbench.families.base import Family, Instance
from orbitbench.families.canary import CanaryFamily
from orbitbench.families.circularize_plan import CircularizePlanFamily
from orbitbench.families.escape_velocity import EscapeVelocityFamily
from orbitbench.families.finite_burn_raise import FiniteBurnRaiseFamily
from orbitbench.families.frame_trap import FrameTrapFamily
from orbitbench.families.guess_trap_transfer import GuessTrapTransferFamily
from orbitbench.families.hohmann import HohmannFamily
from orbitbench.families.hohmann_or_bielliptic_plan import HohmannOrBiellipticPlanFamily
from orbitbench.families.ill_posed import KINDS, IllPosedFamily
from orbitbench.families.j2_drift import J2DriftFamily
from orbitbench.families.plane_change_budget_plan import PlaneChangeBudgetPlanFamily
from orbitbench.families.plane_change_dv import PlaneChangeDvFamily
from orbitbench.families.rendezvous_phasing import RendezvousPhasingFamily
from orbitbench.families.state_at_date import StateAtDateFamily
from orbitbench.families.sun_synchronous import SunSynchronousFamily
from orbitbench.families.tle_state import TleStateFamily
from orbitbench.families.tsiolkovsky import TsiolkovskyFamily

FAMILIES = {family.name: family for family in (HohmannFamily(), PlaneChangeDvFamily(), StateAtDateFamily(),
                                                       TleStateFamily(), J2DriftFamily(),
                                                       CircularizePlanFamily(), HohmannOrBiellipticPlanFamily(),
                                                       PlaneChangeBudgetPlanFamily(), FrameTrapFamily(),
                                                       GuessTrapTransferFamily(), SunSynchronousFamily(),
                                                       RendezvousPhasingFamily(), FiniteBurnRaiseFamily(), CanaryFamily(),
                                                       TsiolkovskyFamily(), EscapeVelocityFamily(),
                                                       *(IllPosedFamily(k, w) for k in KINDS for w in (False, True)))}


def generate(family: str, seed: int, mode: str) -> Instance:
    return FAMILIES[family].generate(seed, mode)


__all__ = ["FAMILIES", "Family", "Instance", "generate"]
