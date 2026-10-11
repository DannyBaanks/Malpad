# cursor_state search — checkpoints and bounds (Fase 3)

Date: 2026-10-11. Gate under test: **cursor_state** — a tape cell that
increments/decrements across iterations in response to LEFT (0x11) / RIGHT
(0x12) input bytes (`tools/malbolge_compiler.py`, MALPAD_STATUS compiler row).

## What lives here

| file | what |
|---|---|
| `smoke_*.json` | harness validation, `op*` ≤4 from truth-machine seed |
| `linear_op_max9_*.json` | census `op*` ≤9 from seed(steps=34): **0 / 29,523** |
| `extended_seeded100_*.json` | census `op*</i` ≤6 from seed(steps=100): **0 / 55,986** |
| `linear_op_max13_*.json`, `extended_opi_max9_*.json` | deep censuses (see below) |
| `mbir_alu_cursor_probe.json` | MBIR-lowering probe: NEGATIVE, with vectors |

Acceptance (straight census): from the mid-loop truth-machine snapshot, the
fragment must change EXACTLY one tape cell by digital-root ±1 (mod 3^10),
advance c/d linearly and emit nothing. Jump-form fragments are evaluated by
the same rule and rejected (recorded, not hidden).

## MBIR lowering probe (negative, canonical)

The MB-DATABASE unified-ALU binary (`mbir_alu.mb`, sha256 `8869f7a1…`) passes
all 14 upstream receipt cases — including alternating chains (ADD→SUB, SUB→ADD)
— on our own oracle_classic re-run. But the exact cursor shapes fail:

| case | expected | actual |
|---|---|---|
| PUSH2 PUSH1 ADD PUSH1 ADD OUT (RR) | `04` | `c6` |
| PUSH3 PUSH1 SUB PUSH1 SUB OUT (LL) | `01` | `e3` |
| ADD OUT then ADD OUT (render per event) | `0304` | `0254` |

Same-opcode chains and post-OUT arithmetic produce garbage; the upstream
receipt never tested them. This matches the MB-DATABASE team's own open
defect (LT_STATUS commits `d2ec624`, `0308c81`: "result never lands in Slot
0"). Cursor-via-VM lowering is therefore **NOT_DEMONSTRATED pending the
Slot-0 propagation fix upstream** — recorded, not hidden.

## Prior bounds this search extends

GENEALOGIA_MALBOLGE: P2′ 37,376 cold candidates (len 3–5) 0 hits; P4′ 2.1M
(len 7) 0 loop-stateful; shortest looping program 170 chars (truth machine).

## Status

`cursor_state: NOT_DEMONSTRATED` remains until a census hit is witnessed or
the MBIR chain defect is fixed and re-probed. Deep censuses (op* ≤13, extended
≤9) run here with explicit timeboxes; all outputs — including zeros — are
canonical evidence (append-only).
