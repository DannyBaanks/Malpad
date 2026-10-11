# MALPAD — M1 quit-on-sentinel gate evidence

Date: 2026-10-11. Milestone: **M1 (echo loop that halts on QUIT 0x04)**.
Supersedes the `quit on sentinel: NOT_DEMONSTRATED` row of
`evidence/m1_echo/GATES.md` (append-only correction added there).

## Gate: `M1_SENTINEL_PASS`

**Status: DEMONSTRATED.**

| Requirement | Status | Evidence |
|---|---|---|
| emit each input byte verbatim | DEMONSTRATED | all vectors, 2/2 interpreters byte-exact |
| byte 0x04 → HALT, sentinel NOT emitted | DEMONSTRATED | `\x04`→``, `AB\x04`→`AB`, `MALPAD\x04rest`→`MALPAD` |
| EOF → HALT | DEMONSTRATED | `ABC`→`ABC` HALTED on both interpreters |
| ≥2 independent interpreters agree | DEMONSTRATED | malbolge.c (C reference ELF) + oracle_classic.py (independent Python, Classic 3^10) |
| long input | DEMONSTRATED | 44-byte vector, 174 779 steps, exact |

## Specimen

- `src/m1_quit_sentinel.hell` — fused HeLL (sha256 in receipts):
  value-dispatch chain of `base_dispatch5.hell` (proven 21/21 in
  MALBOLGE-MB-DATABASE `byte_dispatch18`) + the proven loop/reset machinery of
  `mbir_a04_gate` (7/7) + `dispatch_04` replaced by bare HALT (the sentinel
  branch) + ENTRY read routed through `MOVED` (R_MOVED restore at handler
  entries, per the MOVED self-destruct rule).
  Generated deterministically by `tools/m1_sentinel_gen.py` (anchor asserts;
  every patch fails loudly if its host code drifts).
- `build/m1_quit_sentinel.mb` — 42 565 B,
  sha256 `6dcf393cbde1c6f034aaf0fc95804e66dfeb9b41bdbd4a5e98604585f4b983fd`.
  Assembled with LMAO v0.6.0. **LMAO output is not byte-reproducible across
  runs** (rand() NOP padding): this exact `.mb` is the canonical specimen; the
  sha256 pins it. Regenerating from HeLL requires re-verification.

## Vectors (raw results: `receipts/m1_quit_sentinel_receipts.json`)

| input (hex) | expected | C ref | oracle_classic |
|---|---|---|---|
| `04` | `` | PASS 46 977 steps | PASS 46 977 |
| `414204` | `4142` | PASS 55 521 | PASS 55 521 |
| `4d414c504144 04 72657374` | `4d414c504144` | PASS 73 219 | PASS 73 219 |
| `414243` (EOF) | `414243` | PASS | PASS 56 098* |
| 44 B mixed + `\x04` + tail | first segment | PASS 174 779 | PASS 174 779 |

\* On pure EOF the two models diverge harmlessly: C sets `a=59048` (classic),
oracle_classic sets `a=-1`; both reach HALT with identical output; step counts
differ only on that vector.

## Interpreter coverage note

The monorepo toolkit `MalbolgeInterpreter` **cannot** witness this specimen: it
halts at `program_end` and never wraps `d` as a 3^10 ring, while LMAO output
relies on ring wrap (MemoryLimitExceededError at ~step 55k). This is a model
difference, not a specimen defect; the two Classic-accurate interpreters above
are the independent witnesses required by the evidence rule.

## Reproduce

```
cd evidence/m1_quit_sentinel
../../tools/m1_sentinel_gen.py src/base_dispatch5.hell -o src/m1_quit_sentinel.hell
"<MALBOLGE-MB-DATABASE>/third_party/lmao/bin/lmao" -o build/m1_quit_sentinel.mb src/m1_quit_sentinel.hell
# verify sha256 matches THIS canonical .mb before trusting; otherwise re-run vectors
python3 -m pytest ../../tests/test_m1_sentinel.py -q
```
