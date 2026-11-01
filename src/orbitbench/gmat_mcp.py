# src/orbitbench/gmat_mcp.py
"""Finds the gmat-mcp checkout: orbitbench imports its `core` from there until gmat-mcp is packaged."""
import os
import sys
from pathlib import Path

ENV_VAR = "GMAT_MCP_PATH"


def checkout_path() -> Path:
    """$GMAT_MCP_PATH, else a sibling folder named GMAT-MCP next to this repository."""
    if os.environ.get(ENV_VAR):
        return Path(os.environ[ENV_VAR])
    return Path(__file__).resolve().parents[2].parent / "GMAT-MCP"


def add_to_path() -> bool:
    """Makes `core` importable. Appended, never prepended, so it cannot shadow this environment's packages."""
    path = checkout_path()
    if not (path / "core").is_dir():
        return False
    if str(path) not in sys.path:
        sys.path.append(str(path))
    return True
