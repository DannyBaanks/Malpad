"""Locate the `malbolge` toolkit checkout and put it (plus this repo) on sys.path.

Shared by conftest.py and by the subprocess code blocks in the cross-VM tests,
which start from a clean interpreter and need the same resolution rules.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_toolkit() -> Path | None:
    candidates = []
    env = os.environ.get("MALBOLGE_TOOLKIT_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(ROOT.parent.parent / "ISyCo" / "workspace" / "malbolge_toolkit")
    candidates.append(ROOT.parent / "workspace" / "malbolge_toolkit")
    for c in candidates:
        if (c / "malbolge" / "__init__.py").is_file():
            return c
    return None


def apply() -> Path | None:
    """Insert repo root, tools/ and the toolkit into sys.path. Returns toolkit or None."""
    for path in (str(ROOT), str(ROOT / "tools")):
        if path not in sys.path:
            sys.path.insert(0, path)
    toolkit = find_toolkit()
    if toolkit is not None and str(toolkit) not in sys.path:
        sys.path.insert(0, str(toolkit))
    return toolkit
