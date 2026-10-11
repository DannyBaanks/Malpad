#!/usr/bin/env python3
"""MALPAD Fase 3: guided cursor_state fragment search (timeboxed census).

Question: does there exist an op-alphabet fragment F that, executed from a
mid-loop truth-machine snapshot S, leaves a SINGLE recognizable state delta:
exactly one tape cell changed by ternary digital-root +1 (increment) or -1
(decrement), with linear register advance (c=S.c+|F|, d=S.d+|F|, no jumps,
no output)? Such straight-through deltas are the building block for a cursor
cell driven by LEFT(0x11)/RIGHT(0x12) bytes; jump-form deltas are recorded
separately.

Known bounds (GENEALOGIA_MALBOLGE): P2' 37,376 cold candidates 0 hits;
P4' 2.1M at len 7, 0 loop-stateful. This census runs FROM the snapshot,
not cold, over "op*" and extended alphabets up to --max-depth, with a hard
wall-clock budget. Every run writes canonical checkpoints (counts + hits) to
evidence/cursor_state_search/ regardless of outcome.

Usage:
    py tools/cursor_state_search.py --max-depth 6 --budget 600 --execute
    py tools/cursor_state_search.py --alphabet 'op*i jp' --max-depth 8 --budget 5400
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.malpad_bootstrap import apply as _apply_bootstrap

_apply_bootstrap()

from malbolge import MalbolgeInterpreter
from malbolge.encoding import normalize

MOD = 3 ** 10  # 59049 — classic word ring
TRUTH_MACHINE = (
    Path(__file__).resolve().parent.parent
    / "evidence" / "m2_state" / "truth_machine.mal"
)
OUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "evidence" / "cursor_state_search"
)


def seed_snapshot(interp, seed_steps: int):
    from malbolge.interpreter import StepLimitExceededError
    tm_ops = normalize(TRUTH_MACHINE.read_text(encoding="ascii"))
    try:
        r = interp.execute("".join(tm_ops), input_buffer=iter("1"),
                           max_steps=seed_steps, capture_machine=True)
        return r.machine
    except StepLimitExceededError:
        # the toolkit aborts without a result object, but the live machine
        # holds the exact mid-loop state at abort: snapshot it directly.
        return interp.machine.copy()


def cell_of_interest(S):
    # truth-machine mutates position 38 across iterations (MALPAD_STATUS);
    # census watches ALL cells but labels the canonical one.
    return 38


def classify_fragment(S, ops, interp):
    """Execute straight fragment from snapshot; return delta classification."""
    try:
        r = interp.execute_from_snapshot(S, ops, max_steps=300)
    except Exception as e:
        return {"error": str(e)[:120]}
    M = r.machine
    if M is None:
        return {"error": "no machine"}
    n = len(ops)
    linear_c = (M.c == (S.c + n) % MOD) and (M.d == (S.d + n) % MOD)
    min_len = min(len(S.tape), len(M.tape))
    changed = [(k, S.tape[k], M.tape[k]) for k in range(min_len)
               if S.tape[k] != M.tape[k]]
    def dr_inc(a, b):
        return b % MOD == (a + 1) % MOD
    def dr_dec(a, b):
        return b % MOD == (a - 1) % MOD
    hits = []
    for k, a, b in changed:
        kind = "inc1" if dr_inc(a, b) else ("dec1" if dr_dec(a, b) else "other")
        hits.append({"cell": k, "old": a, "new": b, "kind": kind})
    single_dr = ([h for h in hits if h["kind"] in ("inc1", "dec1")])
    return {
        "output_len": len(r.output),
        "output_hex": r.output.encode("latin-1").hex(),
        "linear": linear_c,
        "changed_cells": len(changed),
        "dr_deltas": single_dr,
        "all_changes": hits[:8],
        "cursor_hit": bool(linear_c and len(changed) == 1
                           and single_dr and not r.output),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alphabet", default="op*",
                    help="single chars used as candidate opcodes")
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--budget", type=float, default=3600,
                    help="wall-clock seconds")
    ap.add_argument("--seed-steps", type=int, default=34)
    ap.add_argument("--tag", default="census")
    ap.add_argument("--execute", action="store_true",
                    help="alias kept for CLI symmetry (census always executes)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_file = OUT_DIR / f"{args.tag}_{stamp}.json"

    interp = MalbolgeInterpreter()
    try:
        S = seed_snapshot(interp, args.seed_steps)
    except Exception as e:
        print(f"seed failed: {e}", file=sys.stderr)
        return 2
    print(f"seed: a={S.a} c={S.c} d={S.d} tape_len={len(S.tape)}")

    chars = [c for c in args.alphabet if c.strip()]
    t0 = time.time()
    per_depth = {}
    cursor_hits = []
    exhausted = True
    for depth in range(1, args.max_depth + 1):
        n_at_depth = 0
        for combo in itertools.product(chars, repeat=depth):
            if time.time() - t0 > args.budget:
                exhausted = False
                break
            ops = "".join(combo)
            res = classify_fragment(S, ops, interp)
            n_at_depth += 1
            if res.get("cursor_hit"):
                cursor_hits.append({"ops": ops, **res})
        per_depth[depth] = n_at_depth
        print(f"depth {depth}: {n_at_depth} candidates, "
              f"hits so far {len(cursor_hits)}, "
              f"{time.time()-t0:.1f}s", flush=True)
        if not exhausted:
            break

    payload = {
        "schema": "malpad-cursor-state-census/1",
        "tag": args.tag,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "alphabet": chars,
        "max_depth_requested": args.max_depth,
        "seed_steps": args.seed_steps,
        "seed": {"a": S.a, "c": S.c, "d": S.d, "tape_len": len(S.tape),
                 "machine_hash": hex(abs(hash(tuple(S.tape[:100]))))},
        "acceptance": "single cell delta +/-1 (mod 3^10), linear c/d, no output",
        "candidates_evaluated": sum(per_depth.values()),
        "per_depth": per_depth,
        "exhaustive": exhausted,
        "elapsed_seconds": round(time.time() - t0, 1),
        "cursor_hits": cursor_hits,
        "note": ("negative census = canonical bound per MALPAD rules; "
                 "truth-machine mutation cell (38) context: "
                 "https://internal GENEALOGIA_MALBOLGE P2'/P4'"),
    }
    out_file.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out_file}")
    print(f"cursor_hits: {len(cursor_hits)} of {payload['candidates_evaluated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
