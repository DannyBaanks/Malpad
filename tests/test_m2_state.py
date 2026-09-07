"""MALPAD M2 — input-branching primitive + frozen editor vectors.

M2 requires Malbolge to maintain editor state and branch on input. The hard
primitive (input-value decision + conditional termination) is demonstrated by a
real Malbolge truth-machine on independent interpreters. The full editor state
machine is the target; its expected semantics are frozen in
editor_state_vectors.json (produced by the M0 IR oracle).
"""
from __future__ import annotations

import os

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TM = ROOT / "evidence" / "m2_state" / "truth_machine.mal"


def _tm_source() -> str:
    return TM.read_text(encoding="utf-8")


def _oracle(inp, steps=2000):
    import sys
    d = os.environ.get("MALPAD_ORACLE_DIR")
    if not d or not Path(d).is_dir():
        pytest.skip("malbolge-oracle not present (set MALPAD_ORACLE_DIR)")
    if d not in sys.path:
        sys.path.insert(0, d)
    from oracle import Oracle
    o = Oracle()
    o.load_ascii(_tm_source())
    o.provide_input(inp)
    return o.run(steps)


def _engine(inp, steps=2000):
    import subprocess, json
    exe = os.environ.get("MALPAD_ENGINE_EXE")
    if not exe or not Path(exe).exists():
        pytest.skip("malbolge-engine not present (set MALPAD_ENGINE_EXE)")
    p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    json.loads(p.stdout.readline())
    p.stdin.write(json.dumps({"id": 1, "op": "run", "program": _tm_source(),
                              "steps": steps, "input": inp}) + "\n")
    p.stdin.flush()
    r = json.loads(p.stdout.readline())
    p.kill()
    return r


def test_truth_machine_input_0_halts():
    ro = _oracle("0")
    assert ro.output.startswith("0")
    assert ro.halted and ro.halt_reason == "halt_opcode"
    re_ = _engine("0")
    assert re_["status"] == "OK" and re_["output"] == "0"


def test_truth_machine_input_1_loops():
    ro = _oracle("1")
    assert ro.output.startswith("1" * 10)
    assert not ro.halted  # loops
    re_ = _engine("1")
    assert re_["status"] == "TIMEOUT"  # still running at budget
    assert re_["output"].startswith("1" * 10)


def test_truth_machine_cross_backend_agreement():
    ro0, re0 = _oracle("0"), _engine("0")
    ro1, re1 = _oracle("1"), _engine("1")
    # both backends agree: 0 -> halt with '0', 1 -> loop with '1'
    assert re0["output"] == "0"
    assert ro0.output == "0"
    assert ro1.output.startswith("1")
    assert re1["output"].startswith("1")


def test_editor_state_vectors_are_frozen_and_match_oracle():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from editor_ir import run_script
    vec = json.loads((ROOT / "tests" / "editor_state_vectors.json").read_text(encoding="utf-8"))
    assert vec["schema"].startswith("malpad.editor_state_vectors")
    for v in vec["vectors"]:
        events, snap = run_script(bytes.fromhex(v["input_hex"]))
        assert snap == v["final"], f"vector {v['name']} drifted: {snap} != {v['final']}"
        assert events == v["events"], f"vector {v['name']} event drift"