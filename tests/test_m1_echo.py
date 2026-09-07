"""MALPAD M1 — Malbolge echo loop (cross-backend).

The M1 program is a real classic Malbolge cat (esolangs), no semantic helper.
It must echo input deterministically on independent interpreters. Oracle and
Malbolge-Engine are the two independent 3^10 backends that feed input.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

M1 = Path(__file__).resolve().parent.parent / "evidence" / "m1_echo" / "program.mal"


def _cat_source() -> str:
    return (M1).read_text(encoding="utf-8")


def _engine_echo(input_s, steps=5000):
    import subprocess, json
    src = _cat_source()
    exe = os.environ.get("MALPAD_ENGINE_EXE")
    if not exe or not Path(exe).exists():
        pytest.skip("malbolge-engine not present (set MALPAD_ENGINE_EXE)")
    p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    json.loads(p.stdout.readline())
    p.stdin.write(json.dumps({"id": 1, "op": "run", "program": src,
                              "steps": steps, "input": input_s}) + "\n")
    p.stdin.flush()
    r = json.loads(p.stdout.readline())
    p.kill()
    return r


def _oracle_echo(input_s, steps=5000):
    import sys
    d = os.environ.get("MALPAD_ORACLE_DIR")
    if not d or not Path(d).is_dir():
        pytest.skip("malbolge-oracle not present (set MALPAD_ORACLE_DIR)")
    if d not in sys.path:
        sys.path.insert(0, d)
    from oracle import Oracle
    o = Oracle()
    o.load_ascii(_cat_source())
    o.provide_input(input_s)
    r = o.run(steps)
    return r


@pytest.mark.parametrize("inp", ["A", "ABC", "HELLO"])
def test_echo_matches_on_engine_and_oracle(inp):
    re_ = _engine_echo(inp)
    ro = _oracle_echo(inp)
    assert re_["output"] == inp, f"engine echo failed: {re_['output']!r}"
    assert ro.output.startswith(inp), f"oracle echo failed: {ro.output!r}"
    assert re_["output"] == ro.output[:len(inp)]


def test_empty_input_clean_on_engine():
    r = _engine_echo("")
    assert r["status"] == "OK"
    assert r["output"] == ""


def test_echo_is_deterministic():
    a = _engine_echo("ABC")["output"]
    b = _engine_echo("ABC")["output"]
    assert a == b == "ABC"