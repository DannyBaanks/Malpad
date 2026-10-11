"""Gate tests for M1 quit-on-sentinel (evidence/m1_quit_sentinel/).

The canonical specimen is pinned by sha256: LMAO output is not
byte-reproducible across runs (rand() NOP padding), so any drift in the
.mb under verification invalidates the receipts and must fail loudly.

Verification runs the pinned specimen on independent Classic interpreters:
  1. tools/oracle_classic.py (MALBOLGE-MB-DATABASE, independent Python 3^10)
  2. runners/malbolge-original/malbolge (C reference ELF)
Both must reproduce byte-exact outputs for the sentinel vectors.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence" / "m1_quit_sentinel"
SPECIMEN = EVIDENCE / "build" / "m1_quit_sentinel.mb"
SPECIMEN_SHA256 = (
    "6dcf393cbde1c6f034aaf0fc95804e66dfeb9b41bdbd4a5e98604585f4b983fd"
)

# Vector: (name, input, expected output). 0x04 = QUIT sentinel, never emitted.
VECTORS = [
    ("sentinel_only", b"\x04", b""),
    ("two_bytes_then_quit", b"AB\x04", b"AB"),
    ("quit_mid_input", b"MALPAD\x04rest", b"MALPAD"),
    ("eof_without_sentinel", b"ABC", b"ABC"),
    (
        "long_mixed",
        b"MALPAD editor m1\nsegunda linea\x04descarta",
        b"MALPAD editor m1\nsegunda linea",
    ),
]


def _mb_database() -> Path | None:
    env = os.environ.get("MALBOLGE_MB_DATABASE_DIR")
    candidates = [Path(env)] if env else []
    candidates.append(ROOT.parent / "MALBOLGE-MB-DATABASE")
    for c in candidates:
        if (c / "tools" / "oracle_classic.py").is_file():
            return c
    return None


def _oracle_classic():
    db = _mb_database()
    if db is None:
        pytest.skip("MALBOLGE-MB-DATABASE not found (set MALBOLGE_MB_DATABASE_DIR)")
    sys.path.insert(0, str(db / "tools"))
    try:
        import oracle_classic
    finally:
        sys.path.pop(0)
    return oracle_classic


def test_specimen_present_and_pinned():
    if not SPECIMEN.is_file():
        pytest.skip("canonical specimen not built (see evidence/m1_quit_sentinel/GATES.md)")
    digest = hashlib.sha256(SPECIMEN.read_bytes()).hexdigest()
    assert digest == SPECIMEN_SHA256, (
        f"specimen drift: LMAO is not byte-reproducible; re-verifying this .mb "
        f"against receipts is required before any claim. got {digest}"
    )


def test_m1_sentinel_oracle_classic():
    oracle = _oracle_classic()
    if not SPECIMEN.is_file():
        pytest.skip("canonical specimen not built")
    prog = SPECIMEN.read_text(encoding="ascii")
    for name, inp, want in VECTORS:
        out, steps, status = oracle.run(prog, 2_000_000, inp.decode("latin-1"))
        got = out.encode("latin-1")
        assert status == "HALTED", f"{name}: status={status}"
        assert got == want, f"{name}: got {got.hex()} want {want.hex()}"


def test_m1_sentinel_c_reference():
    db = _mb_database()
    if db is None:
        pytest.skip("MALBOLGE-MB-DATABASE not found")
    runner = db / "runners" / "malbolge-original" / "malbolge"
    if not runner.is_file():
        pytest.skip("C reference interpreter not present")
    if not SPECIMEN.is_file():
        pytest.skip("canonical specimen not built")
    for name, inp, want in VECTORS:
        p = subprocess.run(
            [str(runner), str(SPECIMEN)], input=inp,
            capture_output=True, timeout=600,
        )
        got = p.stdout
        if got.endswith(b"\n"):
            got = got[:-1]  # the reference program's closing newline
        assert got == want, f"{name}: got {got.hex()} want {want.hex()}"
