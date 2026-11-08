# src/orbitbench/families/lunar_impact.py
"""Date at which a low lunar orbit decays to the surface. The reference comes from GMAT (GRGM900C, degree 50) and is
read from a table built once by scripts/build_lunar_table.py: the answer needs data a model cannot recall or download."""
import os
from importlib import resources
from pathlib import Path

import yaml

from orbitbench.answer import Claims, FinalAnswer
from orbitbench.constants import SATELLITE
from orbitbench.families.base import Family, Instance, answer_format, fill, load_template
from orbitbench.families.lunar_draw import ELEMENTS, MOON_RADIUS_KM

KEYS = ("impact_days",)
TABLE = "lunar_impact_table"


PRIVATE_ENV = "ORBITBENCH_LUNAR_PRIVATE_TABLE"


def private_table_path() -> Path:
    """The test seeds' table: kept out of the repository (private/ is git-ignored), or the file named by the environment."""
    return Path(os.environ.get(PRIVATE_ENV) or Path("private") / f"{TABLE}.yaml")


def load_table() -> dict:
    """seed -> {params, impact_days, rejected}: the public table of the development seeds, plus the private table of the
    test seeds when its file exists. Empty if neither has been built."""
    path = resources.files("orbitbench.families").joinpath("templates", f"{TABLE}.yaml")
    rows = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    table = {int(k): v for k, v in (rows or {}).items()}
    private = private_table_path()
    if private.is_file():
        for k, v in (yaml.safe_load(private.read_text(encoding="utf-8")) or {}).items():
            if int(k) in table:
                raise ValueError(f"seed {k} is in both the public and the private lunar table")
            table[int(k)] = v
    return table


class LunarImpactFamily(Family):
    name = "lunar_impact"

    def __init__(self):
        self.template = load_template("lunar_impact")

    def _row(self, seed: int) -> dict:
        row = load_table().get(seed)
        if row is None:
            raise KeyError(f"seed {seed} is not in {TABLE}.yaml: build it with scripts/build_lunar_table.py")
        return row

    def generate(self, seed: int, mode: str) -> Instance:
        if mode != "values":
            raise ValueError("lunar_impact is answered with values only")
        tpl, row = self.template, self._row(seed)
        p = dict(row["params"])
        tol = tpl["tolerance"]["impact_days"]
        fields = dict(satellite=SATELLITE, impact_radius=MOON_RADIUS_KM, max_days=tpl["max_days"], tol=tol,
                      degree=tpl["gravity"]["degree"], order=tpl["gravity"]["order"], **p)
        statement = "\n\n".join([fill(tpl["statement"]["common"], fields), fill(tpl["statement"]["values"], fields),
                                 answer_format(mode, SATELLITE, KEYS)])
        return Instance(
            family=self.name, mode=mode, seed=seed, level=tpl["levels"][mode], statement=statement,
            epoch=p["epoch"], final_epoch=p["epoch"], satellite=SATELLITE,
            initial_state={"type": "keplerian", **{k: p[k] for k in ELEMENTS}},
            tolerances={"impact_days": tol},
            params={**p, "impact_days": row["impact_days"], "rejected": row["rejected"], "central_body": "Luna"},
            gravity=dict(tpl["gravity"]))

    def reference_values(self, instance: Instance) -> dict:
        return {"impact_days": float(instance.params["impact_days"])}

    def reference(self, instance: Instance) -> FinalAnswer:
        return FinalAnswer(schema_version="1.0", status="solved", values=self.reference_values(instance),
                           claims=Claims(verified=True, method="gmat_grgm900c_degree_50"))
