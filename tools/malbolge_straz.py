#!/usr/bin/env python3
"""MALBOLGE-STRAZ: two-phase (metachar -> token) primitives for Malbolge output.

For each byte value b in 0..255 we synthesize:
    [metachar for b]  ->  [b]
whose total console output is exactly <M_b><b>  (metachar letter, then the byte).
Composition writes, per input byte, the metachar then the byte, so the console
ends up with <META0 b0 META1 b1 ...>.  The "STRAZ" stream is the visible
uppercase-stream; the payload is what's between the uppercase letters.

Honest status (evidence/malbolge_straz/GATES.md):
  - per-byte two-phase synthesis VERIFIED byte-exact from bootstrap state
  - composition of a message VERIFIED byte-exact (see GATES)
  - the primitives are STATE-BOUND: a delta is only valid from the machine
    state it was synthesized at. A state-independent "fixed alphabet" is
    NOT_DEMONSTRATED (anchor/bridge machinery in the translator is broken).

CLI:
    py tools/malbolge_straz.py --synth-alphabet [--from-byte 0 --to-byte 64]
    py tools/malbolge_straz.py --compose-file msg.txt --execute
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from malbolge import GenerationConfig, MalbolgeInterpreter, ProgramGenerator
from malbolge.generator import _GenerationStats, _PrefixState

BOOTSTRAP = "i" + "o" * 99
HALT = "v"

ROOT = Path(__file__).resolve().parent.parent
STRAZ_DIR = ROOT / "evidence" / "malbolge_straz"
ALPHABET_DIR = STRAZ_DIR / "alphabet"          # per-byte receipt jsonl

# Uppercase metachars assigned round-robin; deterministic and documented.
UPPER = [chr(c) for c in range(ord("A"), ord("Z") + 1)]


def metachar_for(byte: int) -> str:
    """Deterministic metachar map: byte -> one uppercase letter (mod 26)."""
    return UPPER[byte % 26]


class StrazComposer:
    def __init__(self, depth: int = 5):
        self.generator = ProgramGenerator()
        self.interp = MalbolgeInterpreter()
        self.depth = depth
        boot = self.interp.execute(BOOTSTRAP, capture_machine=True)
        assert boot.machine is not None
        self.boot_machine = boot.machine

    def synth(self, machine, prefix_ops: str, target_latin1: str) -> str:
        """Search opcodes that extend prefix so output grows by target_latin1."""
        cfg = GenerationConfig(opcode_choices="op*",
                               max_search_depth=self.depth, random_seed=42)
        stats = _GenerationStats()
        cache: dict = {}
        dead: set = set()
        cur = _PrefixState(opcodes=prefix_ops, output="", machine=machine.copy())
        for idx in range(len(target_latin1)):
            tpref = target_latin1[: idx + 1]
            found = False
            combos = list(cfg.opcode_choices)
            depth = 0
            while not found:
                depth += 1
                for cand in combos:
                    suf = cand + "<"
                    if cur.opcodes + suf in dead:
                        continue
                    cs, _ = self.generator._get_or_extend_state(
                        cur, suf, self.interp, cfg, cache, stats)
                    if cs.machine is None:
                        continue
                    out = cs.output
                    if target_latin1.startswith(out) and len(out) <= len(target_latin1) \
                            and out == tpref:
                        cur = cs
                        found = True
                        break
                if found:
                    break
                combos = [b + o for b in combos for o in cfg.opcode_choices
                          if (cur.opcodes + b + o + "<") not in dead]
                if not combos:
                    raise RuntimeError(f"search exhausted at {tpref!r}")
                if depth >= cfg.max_search_depth:
                    viable = [c for c in combos
                              if (cur.opcodes + c + "<") not in dead]
                    if not viable:
                        combos = list(cfg.opcode_choices)
                        depth = 0
                        continue
                    rs, _ = self.generator._get_or_extend_state(
                        cur, viable[0], self.interp, cfg, cache, stats)
                    if rs.machine is None:
                        continue
                    cur = rs
                    combos = list(cfg.opcode_choices)
                    depth = 0
        return cur.opcodes[len(prefix_ops):]

    def synth_byte(self, byte: int) -> dict:
        """From bootstrap: metachar then byte; verify; return receipt + ops."""
        meta = metachar_for(byte)
        t0 = time.time()
        d_meta = self.synth(self.boot_machine, BOOTSTRAP, meta)
        r1 = self.interp.execute_from_snapshot(self.boot_machine, d_meta,
                                               capture_machine=True)
        assert r1.output == meta, f"metachar synth wrong: {r1.output!r}"
        d_tok = self.synth(r1.machine, BOOTSTRAP + d_meta,
                           chr(byte))
        program = BOOTSTRAP + d_meta + d_tok + HALT
        r2 = self.interp.execute(program, capture_machine=True)
        out_bytes = r2.output.encode("latin-1")
        ok = (out_bytes == meta.encode("latin-1") + bytes([byte])
              and r2.halt_reason == "halt_opcode")
        return {
            "byte": byte,
            "byte_hex": f"{byte:02x}",
            "metachar": meta,
            "program_ops": len(program),
            "meta_delta": d_meta,
            "token_delta": d_tok,
            "output_hex": out_bytes.hex(),
            "byte_exact": ok,
            "steps": r2.steps,
            "seconds": round(time.time() - t0, 2),
        }


def _receipt_path(byte: int) -> Path:
    return ALPHABET_DIR / f"{byte:03d}.json"


def synth_alphabet(a: int, b: int, timeout: float = 300.0) -> None:
    """Per-byte child processes with wall-clock timeout; resume-safe."""
    import subprocess
    import sys
    ALPHABET_DIR.mkdir(parents=True, exist_ok=True)
    n_ok = n_fail = n_to = 0
    for byte in range(a, b + 1):
        p = _receipt_path(byte)
        if p.exists():
            prev = json.loads(p.read_text(encoding="utf-8"))
            if prev.get("byte_exact"):
                print(f"[skip] byte {byte} already verified")
                n_ok += 1
                continue
        rc = None
        try:
            proc = subprocess.run(
                [sys.executable, __file__, "--synth-one", str(byte)],
                timeout=timeout, capture_output=True, text=True)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            p.write_text(json.dumps({
                "byte": byte, "byte_hex": f"{byte:02x}",
                "metachar": metachar_for(byte),
                "byte_exact": False,
                "error": f"TIMEOUT after {timeout}s (synthesis not bounded; "
                         "no proof of impossibility, just budget)",
                "timeout_s": timeout,
            }, indent=1) + "\n", encoding="utf-8")
            print(f"[TIMEOUT] byte {byte:3d} (0x{byte:02x})")
            n_to += 1
            continue
        if rc != 0 or not p.exists():
            if not p.exists():
                p.write_text(json.dumps({
                    "byte": byte, "byte_hex": f"{byte:02x}",
                    "byte_exact": False, "error": f"child exit {rc}",
                }, indent=1) + "\n", encoding="utf-8")
        r = json.loads(p.read_text(encoding="utf-8"))
        mark = "OK " if r.get("byte_exact") else "FAIL"
        print(f"[{mark}] byte {byte:3d} (0x{byte:02x}) ops={r.get('program_ops')} "
              f"t={r.get('seconds')}")
        n_ok += bool(r.get("byte_exact"))
        n_fail += (not r.get("byte_exact"))
    print(f"[alphabet {a}..{b}] verified={n_ok} failed={n_fail} timeouts={n_to}")


def _synth_one(byte: int) -> None:
    """Child entry: synthesize one byte receipt and write it."""
    ALPHABET_DIR.mkdir(parents=True, exist_ok=True)
    comp = StrazComposer()
    try:
        r = comp.synth_byte(byte)
    except Exception as e:
        r = {"byte": byte, "byte_hex": f"{byte:02x}", "metachar": metachar_for(byte),
             "byte_exact": False, "error": f"{type(e).__name__}: {e}"}
    _receipt_path(byte).write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n",
                                   encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="MALBOLGE-STRAZ two-phase primitives")
    ap.add_argument("--synth-alphabet", action="store_true")
    ap.add_argument("--synth-one", type=int, default=None,
                    help="single byte (child mode)")
    ap.add_argument("--byte-timeout", type=float, default=120.0)
    ap.add_argument("--from-byte", type=int, default=0)
    ap.add_argument("--to-byte", type=int, default=255)
    ap.add_argument("--compose-file", type=Path)
    ap.add_argument("--text")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    if args.synth_one is not None:
        _synth_one(args.synth_one)
        return 0
    if args.synth_alphabet:
        synth_alphabet(args.from_byte, args.to_byte, args.byte_timeout)
        return 0
    ap.error("nothing to do (try --synth-alphabet)")


if __name__ == "__main__":
    raise SystemExit(main())
