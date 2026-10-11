# MALPAD — status dashboard (honest, per-milestone)

No global "80% complete" metric. Each milestone is a distinct property with its
own gate and status.

| Milestone | Gate | Status | Evidence |
|-----------|------|--------|----------|
| M0 | contracts frozen | **DEMONSTRATED** | PROTOCOL/STATE_MODEL/HOST_BOUNDARY + 18 tests |
| M1 | echo loop | **DEMONSTRATED** | echo cross-backend (A/ABC/HELLO); quit-on-sentinel DEMONSTRATED 2026-10-11: evidence/m1_quit_sentinel (0x04→HALT, EOF→HALT, 5/5 vectors byte-exact on C reference + oracle_classic) |
| M2 | input branching | **PARTIAL** | truth-machine cross-backend (0→halt, 1→loop); full editor state NOT_DEMONSTRATED |
| M3 | editable buffer in Malbolge | **PARTIAL** (was: seam-only) | host seam: evidence/m3_buffer_authority + tools/buffer_adapter.py + 4 tests. Pure Malbolge end-to-end (reproduce editor_state_vectors.json) NOT_DEMONSTRATED, narrowed 2026-10-11: N-way dispatch + 2-slot persistent store/load + AB→BA reverse now DEMONSTRATED by lineage; open = cursor_state, stack depth>2, shifting. See evidence/m3_buffer/GATES.md Correction + evidence/buffer_mutate/GATES.md |
| M4 | logical render | **DEMONSTRATED** | terminal model from @MALPAD: events, presentation-only |
| M5 | ANSI adapter | **DEMONSTRATED** | model → ANSI, deterministic, backend-independent |
| M7 | save authority seam | **DEMONSTRATED** | request vs authority separated; write/deny/fail + receipts |
| Bridge | Python body ↔ Malbolge brain | **DEMONSTRATED (transport + real oracle)** | generated Malbolge emits @MALPAD: frames, parsed → model → ANSI, backend-independent; oracle now uses real MalbolgeInterpreter (Phase 1) |
| Compiler | IR→Malbolge lowering pipeline | **FRAMEWORK PRESENT / PARTIAL** | lowers read/emit/halt; buffer authority seam DEMONSTRATED (transport only); pure mutable_cell reverse **DEMONSTRATED 2026-10-11** by A05b lineage (evidence/mutable_cell_reverse) |

## Architecture (reframe)

Python is the **body**; Malbolge is the **editor brain**; the byte protocol is
the cable. Python MAY translate `VK_LEFT → LEFT`, NEVER `LEFT → cursor--`.
See `docs/MALPAD_ARCHITECTURE.md`. Win32 is a rear problem (M10); the bridge
+ M4/M5/M7 already define the boundary any frontend connects to.

## Compiler (future)

| IR→Malbolge stateful compiler | STATUS |
|-------------------------------|--------|
| overall | PARTIAL — 5/8 primitives DEMONSTRATED (read, emit, halt-loop, mutable_cell_store, mutable_cell_load); branch PARTIAL; cursor_state y buffer_mutate NOT_DEMONSTRATED |
| read_input / emit / halt-loop primitives | DEMONSTRATED (via existing programs) |
| compare_input / branch | **DEMONSTRATED** (N-way byte-VALUE dispatch por linaje: byte_dispatch18 21/21 MB-DATABASE; fusion MALPAD m1_quit_sentinel 6-way + sentinel, 5/5 dos interpretos) |
| mutable_cell_store | **DEMONSTRATED** (A05b LIFO slot cells; truth-machine also mutates across iterations) |
| mutable_cell_load | **DEMONSTRATED** (A05b pops stored bytes later; order-reversed readback) |
| cursor_state | NOT_DEMONSTRATED — cotas nuevas 2026-10-11: censo exhaustivo straight-delta desde snapshot truth-machine `op*`<=13: 0/2,391,483 y `op*</i`<=9: 0/12,093,234 (evidence/cursor_state_search). Baja por VM MBIR bloqueada por defecto upstream "result never lands in Slot 0" (ADD→ADD/SUB→SUB dan basura; probe canonica incluida). |
| buffer_mutate | NOT_DEMONSTRATED — precise chain in `evidence/buffer_mutate/GATES.md`: N-way dispatch + 2-slot store/load DEMONSTRATED; still open = stack depth>2, indirect addressing, cursor_state, shifting. Corpus search 2026-10-11 (GENEALOGIA/MB-DATABASE/MALBOLGE/MalbolgeFree) found no shift/depth>2 specimen. |
| pure mutable_cell reverse AB->BA | **DEMONSTRATED** (2026-10-11, por linaje A05b LIFO: evidence/mutable_cell_reverse, 7/7 byte-exact C+oracle; specimen sha256 f237df82) |
| validation | generator != oracle, on independent interpreters |

### Negative bounds from GENEALOGIA_MALBOLGE

- **P2'**: ternary non-echo transition — 37,376 candidates (len 3-5), 0 hits
- **P4'**: ternary stateful counter — 2.1M candidates (len 7), 3884 with 3 outputs but 0 with loop
- **long_search**: no length-7 program runs ≥50 steps (0 hits out of 2.1M)
- **Shortest known looping program**: truth_machine.mal (170 chars)
- **Conclusion**: cursor_state requires programs ≥170 chars with self-modifying code + arithmetic

### Resolution route (from GENEALOGIA_MALBOLGE)

1. Use truth_machine.mal as seed for P1 (2-way branch)
2. Extend Autobolge relational/Zig with **persistent state constraints** (not just output)
3. Synthesize P1-P5 separately: each fragment = known input → known output → known final state (anchor)
4. Materialize opcodes via gost codegen (XLAT1 positional encoding)
5. Validate each fragment on **three runtimes**: Oracle, gost, Malbolge-Engine
6. Compose via `AnchorManager.bridge()` + `WordBank` + `fresh_vm_continuation`

See `docs/IR_TO_MALBOLGE_COMPILER_SCOPE.md`.

## Claims earned (M3/M4/M5/M7)

- M3 buffer: the **transport/authority seam** is DEMONSTRATED (host stores/loads
  bytes it is handed; it does not decide editing semantics). The **editable
  buffer-in-Malbolge** gate remains NOT_DEMONSTRATED end-to-end — see
  evidence/m3_buffer/GATES.md Correction (2026-10-11) and
  evidence/buffer_mutate/GATES.md. Dashboard label set to PARTIAL, not a
  promotion.
- The presentation layer (render) is independently testable and backend-neutral
- Save authority is a host-side seam: the core only issues requests; writes are
  behind policy + explicit request, with truthful receipts.

## Test suite

`python3 -m pytest tests -q` → **124 passed, 19 skipped** (Linux, 2026-10-11;
skips are pre-existing env-gated + `test_bridge_v1` random-split-point flakiness,
not regressions). With `MALPAD_ORACLE_DIR=tools` the real-oracle subset runs:
M0 18, M1 echo 5 + sentinel 3, M2 4, M3 buffer 4, M4/M5 6, M7 6, bridge 4,
compiler 9, mutable_cell 2 + reverse 3, cursor_state census, negative controls,
contract, cross_vm, fragment-epoch, primitives reeval, word_bank. See README for
the exact per-file count.
