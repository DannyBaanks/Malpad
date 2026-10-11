# MALPAD — M1 gate evidence

Date: 2026-08-30. Milestone: **M1 (Malbolge echo loop)**.

## Gate: `M1_PASS`

**Status: PARTIAL.**

| M1 requirement | Status | Evidence |
|----------------|--------|----------|
| read char | DEMONSTRATED | Malbolge `/` reads input byte (engine + oracle) |
| emit char | DEMONSTRATED | Malbolge `<` emits byte (engine + oracle) |
| repeat (loop) | DEMONSTRATED | multi-char echo: ABC→ABC, HELLO→HELLO |
| reproducible in >=2 independent interpreters | DEMONSTRATED | Malbolge-Engine (C) + malbolge-oracle (Python reference) produce identical echo |
| empty → clean behavior | DEMONSTRATED (engine) | engine: OK, 34 steps, `""`; oracle: continues (EOF→59048, D3 divergence) |
| quit on sentinel | **NOT_DEMONSTRATED** | program halts at end-of-input (EOF) on engine, but does NOT branch on a specific sentinel byte |

## Program

`evidence/m1_echo/program.mal` — the esolangs classic 3^10 cat (echo loop). No
semantic helper. Provenance: esolangs.org/wiki/Malbolge Sample Programs.

## Cross-backend parity

| input | engine output | oracle output (first N) | match |
|-------|---------------|--------------------------|-------|
| A | `A` (OK, 34? steps) | `A` | yes |
| ABC | `ABC` (OK, 169 steps) | `ABC` | yes |
| HELLO | `HELLO` (OK, 259 steps) | `HELLO` | yes |
| (empty) | `""` (OK, 34 steps) | `""` then continues | echo matches; termination diverges |

Termination divergence is the known E31-A D3 (EOF → `a=59048` oracle vs
terminate engine), not an echo bug.

## Why "quit on sentinel" is NOT_DEMONSTRATED

A Malbolge program that branches on a **specific** input byte and halts requires
input-value comparison inside the loop — the "several orders of magnitude more
complex" cat (per esolangs). The M1 cat halts only at end-of-input on the
engine. Producing a sentinel-branching echo is the M2/M3 precursor hard problem
and is deliberately not overclaimed here.

## Artifacts

- `evidence/m1_echo/program.mal`, `input_{A,ABC,HELLO,empty,demo}.bin`,
  `out_engine_*.txt`, `out_oracle_*.txt`, `output_demo.bin`, `manifest.json`,
  `hashes.sha256`.

## Next

M2 — state and logical cursor (the sentinel/state-branching Malbolge work),
gated by `STATE_MACHINE_DEMONSTRATED`.
## Correction (append, 2026-10-11)

The `quit on sentinel: NOT_DEMONSTRATED` row above is superseded:
`evidence/m1_quit_sentinel/` (GATES.md + receipts) demonstrates a
sentinel-branching echo (0x04 → HALT, sentinel not emitted; EOF → HALT),
byte-exact on 2 independent Classic interpreters across 5 vectors.
Specimen sha256 `6dcf393c…`. This file is kept unmodified as raw history.
