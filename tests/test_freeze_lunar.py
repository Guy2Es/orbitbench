# tests/test_freeze_lunar.py
"""The values frozen for the lunar line of v1.1 (docs/freeze.md, amendment of 8 November 2026). If one of them has to
change, the change is written in docs/freeze.md with its date first, and the value here is updated with it."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from orbitbench.families import generate
from orbitbench.families.base import load_template
from orbitbench.families.lunar_impact import load_table
from orbitbench.harness.catalog import LUNAR_LINES, LUNAR_TEST_LINES

DEV_SEEDS = range(15)
STATEMENTS_SHA256 = "adfd57807017afcfe6dbf62cf7b9a97363cbe56ed636a19a844a503a2e63bb1f"
ROWS_SHA256 = "bc8361bd70645c3fafe7b121f1e358fc8a39198221277355f55bd4a8da18b16f"


def test_the_template_values_are_the_frozen_ones():
    tpl = load_template("lunar_impact")
    assert tpl["tolerance"] == {"impact_days": 1.0}
    assert tpl["max_days"] == 60 and tpl["max_candidates"] == 200
    assert tpl["gravity"] == {"degree": 50, "order": 50, "file": "GRGM900C"}
    assert tpl["epoch_start"] == "01 Jan 2026 00:00:00.000" and tpl["epoch_days"] == 365
    assert tpl["ranges"] == {"periapsis_alt_km": [20.0, 45.0], "ecc": [0.003, 0.008], "inc_deg": [45.0, 85.0],
                             "raan_deg": [0.0, 360.0], "aop_deg": [0.0, 360.0], "ta_deg": [0.0, 360.0]}


def test_the_reference_setting_is_the_frozen_one():
    path = Path(__file__).resolve().parent.parent / "scripts" / "build_lunar_table.py"
    spec = importlib.util.spec_from_file_location("build_lunar_table", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.SETTINGS == {"integrator": "PrinceDormand78", "accuracy": 1e-12, "max_step_s": 300}


def test_the_development_statements_are_the_frozen_ones():
    text = "\n---\n".join(generate("lunar_impact", s, "values").statement for s in DEV_SEEDS)
    assert hashlib.sha256(text.encode()).hexdigest() == STATEMENTS_SHA256


def test_the_development_table_is_the_frozen_one():
    table = load_table()
    rows = [[s, table[s]["impact_days"], table[s]["rejected"], table[s]["params"]] for s in DEV_SEEDS]
    assert hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest() == ROWS_SHA256


def test_the_suites_have_the_frozen_sizes():
    assert LUNAR_LINES == (("lunar_impact", "values", 15),)
    assert LUNAR_TEST_LINES == (("lunar_impact", "values", 30),)


def test_the_test_seeds_do_not_overlap_the_development_seeds():
    table = load_table()
    private = [s for s in table if s not in DEV_SEEDS]
    if not private:
        pytest.skip("no private test table on this machine")
    assert len(private) == 30 and sorted(private) == list(range(min(private), min(private) + 30))
    assert min(private) > 14
