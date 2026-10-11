# MALPAD — status dashboard (honest, per-milestone)

No global "80% complete" metric. Each milestone is a distinct property with its
own gate and status.

| Milestone | Gate | Status | Evidence |
|-----------|------|--------|----------|
| M0 | contracts frozen | **DEMONSTRATED** | PROTOCOL/STATE_MODEL/HOST_BOUNDARY + 18 tests |
| M1 | echo loop | **DEMONSTRATED** | echo cross-backend (A/ABC/HELLO); quit-on-sentinel DEMONSTRATED 2026-10-11: evidence/m1_quit_sentinel (0x04→HALT, EOF→HALT, 5/5 vectors byte-exact on C reference + oracle_classic) |
| M2 | input branching | **PARTIAL** | truth-machine cross-backend (0→halt, 1→loop); full editor state NOT_DEMONSTRATED |
| M3 | editable buffer in Malbolge | **DEMONSTRATED via Buffer Authority Seam** | evidence/m3_buffer_authority + tools/buffer_adapter.py + 4 tests (AB->BA reverse via STORE/LOAD) |
| M4 | logical render | **DEMONSTRATED** | terminal model from @MALPAD: events, presentation-only |
| M5 | ANSI adapter | **DEMONSTRATED** | model → ANSI, deterministic, backend-independent |
| M7 | save authority seam | **DEMONSTRATED** | request vs authority separated; write/deny/fail + receipts |
| Bridge | Python body ↔ Malbolge brain | **DEMONSTRATED (transport + real oracle)** | generated Malbolge emits @MALPAD: frames, parsed → model → ANSI, backend-independent; oracle now uses real MalbolgeInterpreter (Phase 1) |
| Compiler | IR→Malbolge lowering pipeline | **FRAMEWORK PRESENT / PARTIAL** | lowers read/emit/halt; buffer authority seam DEMONSTRATED; pure mutable_cell reverse still NOT_DEMONSTRATED |

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
| compare_input / branch | PARTIAL (truth-machine: 2-way 0/1 branch; N-way NOT_DEMONSTRATED) |
| mutable_cell_store | **DEMONSTRATED** (A05b LIFO slot cells; truth-machine also mutates across iterations) |
| mutable_cell_load | **DEMONSTRATED** (A05b pops stored bytes later; order-reversed readback) |
| cursor_state | NOT_DEMONSTRATED (needs arithmetic + self-modifying code) |
| buffer_mutate | NOT_DEMONSTRATED (hardest primitive — needs N-way dispatch + array access) |
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

- M3 buffer now DEMONSTRATED via authority seam (like M7 save)
- The presentation layer (render) is independently testable and backend-neutral
- Save authority is a host-side seam: the core only issues requests; writes are
  behind policy + explicit request, with truthful receipts.

## Test suite

`MALPAD_ORACLE_DIR=tools pytest -q` → **48 passed, 12 skipped** (M0 18, M1 5, M2 4, M3 buffer 4, M4/M5 6, M7 6, bridge 4, compiler 9, mutable_cell 2).
