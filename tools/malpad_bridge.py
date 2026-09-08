"""MALPAD bridge — Python body ↔ Malbolge backend (the cable).

Hosts a Malbolge program behind the byte protocol. Feeds input bytes to the
backend, reads its @MALPAD: output frames, parses them, and feeds the terminal
model (M4) → ANSI (M5). The save authority seam (M7) plugs in on the host side.

The bridge is the BODY. It never decides editor semantics. Whatever .mal is
behind it determines the editor state (M3). Same bridge, any frontend; same
bridge, any Malbolge backend.

Python MAY translate physical keys -> protocol bytes.
Python MUST NOT translate protocol bytes -> editor state.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

ENGINE_EXE = os.environ.get("MALPAD_ENGINE_EXE")
ORACLE_DIR = os.environ.get("MALPAD_ORACLE_DIR")

FRAME = "@MALPAD:"


@dataclass
class BridgeResult:
    program: str
    backend: str
    raw_output: str
    frames: List[str] = field(default_factory=list)
    final_snapshot: Optional[dict] = None

    def to_dict(self) -> dict:
        return {"program": self.program, "backend": self.backend,
                "raw_output": self.raw_output, "frames": self.frames,
                "final_snapshot": self.final_snapshot}


def run_backend(program: str, backend: str, input_bytes: bytes,
                max_steps: int = 5_000_000) -> str:
    """Run a Malbolge program, feed input, return its stdout output string."""
    if backend == "oracle":
        from oracle import Oracle
        o = Oracle()
        o.load_ascii(program)
        o.provide_input(input_bytes.decode("latin-1"))
        r = o.run(max_steps)
        return r.output
    if backend == "malbolge-engine":
        if not ENGINE_EXE:
            raise RuntimeError(
                "malbolge-engine not configured: set MALPAD_ENGINE_EXE to the "
                "Malbolge-Engine malbolge-ipc.exe path")
        p = subprocess.Popen([ENGINE_EXE], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, text=True)
        import json
        json.loads(p.stdout.readline())
        p.stdin.write(json.dumps({"id": 1, "op": "run", "program": program,
                                  "steps": max_steps,
                                  "input": input_bytes.decode("latin-1")}) + "\n")
        p.stdin.flush()
        resp = json.loads(p.stdout.readline())
        p.kill()
        return resp.get("output", "")
    raise ValueError(f"unknown backend {backend}")


def parse_frames(raw: str) -> List[str]:
    """Split raw output into @MALPAD: frame lines."""
    out = []
    for line in raw.splitlines():
        line = line.rstrip("\r")
        if line.startswith(FRAME):
            out.append(line)
    return out


def run_bridge(program_path: str, backend: str = "oracle",
               input_bytes: bytes = b"", max_steps: int = 5_000_000) -> BridgeResult:
    program = Path(program_path).read_text(encoding="utf-8").strip()
    raw = run_backend(program, backend, input_bytes, max_steps)
    frames = parse_frames(raw)
    from terminal_model import model_from_stream
    m = model_from_stream(frames)
    return BridgeResult(program=program_path, backend=backend,
                        raw_output=raw, frames=frames,
                        final_snapshot=m.snapshot())


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("program")
    ap.add_argument("--backend", default="oracle")
    ap.add_argument("--input-hex", default="", help="input bytes as hex")
    ap.add_argument("--ansi", action="store_true", help="also print ANSI render")
    args = ap.parse_args()
    inp = bytes.fromhex(args.input_hex) if args.input_hex else b""
    r = run_bridge(args.program, args.backend, inp)
    print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))
    if args.ansi:
        from ansi_adapter import render_model
        from terminal_model import model_from_stream
        m = model_from_stream(r.frames)
        print("--- ANSI ---")
        print(repr(render_model(m)))