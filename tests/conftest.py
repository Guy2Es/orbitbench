# tests/conftest.py
"""Shared setup: gmat-mcp's `core` on the path, and the `gmat` tests skipped when GMAT is not available."""
import os

import pytest

from orbitbench import gmat_mcp

CORE_AVAILABLE = gmat_mcp.add_to_path()


def pytest_configure(config):
    config.addinivalue_line("markers", "gmat: needs GMAT R2026a and a gmat-mcp checkout (slow)")


def pytest_collection_modifyitems(config, items):
    if CORE_AVAILABLE and os.environ.get("GMAT_INSTALL"):
        return
    skip = pytest.mark.skip(reason="needs a gmat-mcp checkout (GMAT_MCP_PATH) and GMAT_INSTALL")
    for item in items:
        if "gmat" in item.keywords:
            item.add_marker(skip)
