# MALPAD — pure mutable_cell reverse (AB→BA) gate evidence

Date: 2026-10-11. Supersedes `pure mutable_cell reverse AB->BA: NOT_DEMONSTRATED
(tooling gap)` in `MALPAD_STATUS.md`.

## Gate: `MUTABLE_CELL_REVERSE_PASS`

**Status: DEMONSTRATED.**

Claim: a pure Classic-Malbolge program (no host helper decides semantics)
stores two payload bytes in **mutable tape cells** across loop iterations and
re-emits them in **reversed LIFO order**: `PUSH 0x41, PUSH 0x42, OUT, OUT,
HALT` (`01410142101000`) → `4241` ("BA"). This exercises
mutable_cell_store + mutable_cell_load + reverse-order readback — the exact
primitives the MALPAD compiler row required.

| Requirement | Status | Evidence |
|---|---|---|
| store byte in mutable cell | DEMONSTRATED | slot cells `stack_top`/`stack_top_1`, depth FSM via SLOT flags |
| load from mutable cell later | DEMONSTRATED | OUT pops from cell after subsequent pushes |
| reverse order (AB→BA) | DEMONSTRATED | vector `LIFO_BA`: oracle `4241`, C `4241` |
| ≥2 independent interpreters | DEMONSTRATED | oracle_classic.py + malbolge.c reference, 7/7 |
| byte-exact incl. step agreement | DEMONSTRATED | identical step counts both interpreters all vectors |

## Specimen & lineage

- `mbir_a05_lifo.mb` (51 877 B), sha256
  `f237df8247f5c8dc10157b96f58ba1dc9eff06ecefe916651b1d3aba5a66ed6c` —
  copied verbatim from MALBOLGE-MB-DATABASE `vm_malbolge/src/mbir_a05_lifo.mb`
  (A05b 2-slot LIFO stack machine, generator
  `vm_malbolge/tools/mbir_a05_lifo_gen.py`, HeLL sha256 `36ec275b…`).
- Upstream canonical receipt: `vm_malbolge/evidence/mbir_a05_lifo_smoke.json`
  (2026-10-07, 7/7 on Python oracle + C runner + Zig). The upstream `.mb`
  artifact hash (`7571212d…`) differs from the file on disk because **LMAO is
  not byte-reproducible**; this MALPAD re-verification independently witnesses
  the on-disk specimen `f237df82…` on 2 interpreters — receipts:
  `receipts/mutable_cell_reverse_receipts.json`.
- Semantics are inside Malbolge: the input is a 3-opcode mini instruction
  stream (01 PUSH <byte>, 10 OUT, 00 HALT) executed by the dispatch chain
  inside the specimen; the host only supplies bytes and compares output.

## Bridge caveat (honest scope)

Adopted by lineage, not by MALPAD synthesis: the per-token primitives
(`evidence/malpad_primitives/`) still compose forward-only output; anchor-reset
composition remains open. Autobolge `AnchorManager.bridge()` was repaired the
same day (commit 895ff17): it previously raised NameError / silently returned
empty ops while searching for an output literal. The fixed bridge searches the
**target state** (registers + tape prefix, no output) and now fails explicitly.
Negative bound recorded: no ≤6-op bridge exists from a mid-echo state to the
default anchor — state-reset synthesis is still open (Fase 3).

## Reproduce

```
python3 -m pytest tests/test_mutable_cell_reverse.py -q
```
