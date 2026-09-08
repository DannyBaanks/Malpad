"""MALPAD bridge — Python body ↔ Malbolge backend transport.

Demonstrates the MALPAD runtime end-to-end with REAL Malbolge programs: a
generated frame-emitter .mal produces @MALPAD: output that the bridge parses
into the terminal model. Same program + same input => same frames on independent
backends. Honest: this transports/renders; it is NOT the stateful editor brain
(M3). The frame-emitter emits fixed frames regardless of input.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from malpad_bridge import run_bridge, parse_frames  # noqa: E402

FRAME_MAL = ROOT / "evidence" / "m_bridge" / "frame_full.mal"


def test_frame_emitter_parsed_on_oracle():
    if not FRAME_MAL.exists():
        pytest.skip("frame emitter not generated")
    r = run_bridge(str(FRAME_MAL), backend="oracle")
    assert "@MALPAD:STATUS:READY" in r.frames
    assert "@MALPAD:QUIT" in r.frames
    assert r.final_snapshot["status"] == "READY"
    assert r.final_snapshot["halted"] is True


def test_bridge_backend_independence():
    if not FRAME_MAL.exists():
        pytest.skip("frame emitter not generated")
    ro = run_bridge(str(FRAME_MAL), backend="oracle")
    from malpad_bridge import ENGINE_EXE
    if not ENGINE_EXE or not Path(ENGINE_EXE).exists():
        pytest.skip("malbolge-engine not present")
    re_ = run_bridge(str(FRAME_MAL), backend="malbolge-engine")
    assert ro.frames == re_.frames
    assert ro.final_snapshot == re_.final_snapshot


def test_parse_frames_only_malpad_frames():
    raw = "garbage\n@MALPAD:LINE:0:HI\n@MALPAD:QUIT\nnot a frame\n"
    assert parse_frames(raw) == ["@MALPAD:LINE:0:HI", "@MALPAD:QUIT"]


def test_bridge_renders_to_ansi():
    if not FRAME_MAL.exists():
        pytest.skip("frame emitter not generated")
    r = run_bridge(str(FRAME_MAL), backend="oracle")
    from ansi_adapter import render_model
    from terminal_model import model_from_stream
    ansi = render_model(model_from_stream(r.frames))
    assert "READY" in ansi  # status rendered