"""Gate tests for pure mutable_cell reverse AB->BA (evidence/mutable_cell_reverse/).

The specimen is the A05b 2-slot LIFO stack machine adopted by lineage from
MALBOLGE-MB-DATABASE. It must reproduce the reversed-order vectors byte-exact
on the independent Python oracle (and the C reference when present).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence" / "mutable_cell_reverse"
SPECIMEN = EVIDENCE / "mbir_a05_lifo.mb"
SPECIMEN_SHA256 = (
    "f237df8247f5c8dc10157b96f58ba1dc9eff06ecefe916651b1d3aba5a66ed6c"
)

VECTORS = [
    ("halt", "00", ""),
    ("push_A_out", "01411000", "41"),
    ("seq_AB", "01411001421000", "4142"),
    ("LIFO_BA", "01410142101000", "4241"),
    ("LIFO_top_B", "014101421000", "42"),
]


def _mb_database() -> Path | None:
    env = os.environ.get("MALBOLGE_MB_DATABASE_DIR")
    candidates = [Path(env)] if env else []
    candidates.append(ROOT.parent / "MALBOLGE-MB-DATABASE")
    for c in candidates:
        if (c / "tools" / "oracle_classic.py").is_file():
            return c
    return None


def test_specimen_pinned():
    if not SPECIMEN.is_file():
        pytest.skip("LIFO specimen not present")
    digest = hashlib.sha256(SPECIMEN.read_bytes()).hexdigest()
    assert digest == SPECIMEN_SHA256, f"specimen drift: got {digest}"


def test_reverse_lifo_oracle_classic():
    db = _mb_database()
    if db is None:
        pytest.skip("MALBOLGE-MB-DATABASE not found (set MALBOLGE_MB_DATABASE_DIR)")
    if not SPECIMEN.is_file():
        pytest.skip("LIFO specimen not present")
    sys.path.insert(0, str(db / "tools"))
    try:
        import oracle_classic
    finally:
        sys.path.pop(0)
    prog = SPECIMEN.read_text(encoding="ascii")
    for name, ihex, ohex in VECTORS:
        inp = bytes.fromhex(ihex)
        want = bytes.fromhex(ohex) if ohex else b""
        out, steps, status = oracle_classic.run(
            prog, 2_000_000, inp.decode("latin-1"))
        got = out.encode("latin-1")
        assert status == "HALTED", f"{name}: status={status}"
        assert got == want, f"{name}: got {got.hex()} want {ohex}"


def test_reverse_lifo_c_reference():
    db = _mb_database()
    if db is None:
        pytest.skip("MALBOLGE-MB-DATABASE not found")
    runner = db / "runners" / "malbolge-original" / "malbolge"
    if not runner.is_file() or not SPECIMEN.is_file():
        pytest.skip("C reference or specimen not present")
    for name, ihex, ohex in VECTORS:
        inp = bytes.fromhex(ihex)
        want = bytes.fromhex(ohex) if ohex else b""
        p = subprocess.run([str(runner), str(SPECIMEN)], input=inp,
                           capture_output=True, timeout=600)
        got = p.stdout[:-1] if p.stdout.endswith(b"\n") else p.stdout
        assert got == want, f"{name}: got {got.hex()} want {ohex}"
