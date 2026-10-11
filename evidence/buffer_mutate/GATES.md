# MALPAD — buffer_mutate gate evidence

Date: 2026-10-11. Scope: the IR primitive `buffer_mutate` — insert/delete over
a persistent buffer **inside a classic Malbolge program**, including the
shifting logic (move cell k→k±1 across a data-dependent run).

## Gate: `BUFFER_MUTATE_IN_MALBOLGE`

**Status: NOT_DEMONSTRATED.** Reported with the precise dependency chain, not
papered over. The host-side transport seam lives in
`evidence/m3_buffer_authority` + `tools/buffer_adapter.py` and is NOT this
gate: per the frozen architecture, the host may transport/render, never
decide editing semantics.

## Dependency chain (per component, with its own gate)

| Component | Status | Evidence / bound |
|---|---|---|
| N-way byte-VALUE input dispatch | **DEMONSTRATED** | lineage `byte_dispatch18` 21/21 (MALBOLGE-MB-DATABASE); MALPAD fusion `m1_quit_sentinel` 6-way + sentinel, 5/5 on C reference + oracle_classic (`evidence/m1_quit_sentinel`) |
| persistent mutable cell store/load | **DEMONSTRATED** | A05b 2-slot LIFO (`evidence/mutable_cell_reverse`, 7/7 both interpreters); pure AB→BA reverse DEMONSTRATED by same lineage |
| stack depth > 2 (≥3 simultaneous cells) | **NOT_DEMONSTRATED** | explicit upstream bound, `MALBOLGE-MB-DATABASE/vm_malbolge/A05_STATUS.md` "What is NOT demonstrated": "Storing 3 or more operands simultaneously requires additional slot cells or indirect memory addressing." |
| indirect memory addressing (index-driven cell R/W) | **NOT_DEMONSTRATED** | upstream A05_STATUS lists "In-memory MBIR program loader… into an array of Malbolge cells" as not demonstrated |
| cursor_state (data-dependent counter cell) | **NOT_DEMONSTRATED** | new exhaustive bounds 2026-10-11, `evidence/cursor_state_search`: straight-delta census from truth-machine snapshot `op*`≤13 → 0/2,391,483; `op*/i`≤9 → 0/12,093,234; MBIR-lowering route blocked by upstream defect "result never lands in Slot 0" (probe `mbir_alu_cursor_probe.json`, NEGATIVE) |
| shifting logic (loop copy cell k→k+1, length-dependent) | **NOT_DEMONSTRATED** | composes the two open items: iteration count driven by buffer length needs cursor_state-class arithmetic, AND each step writes a distinct indexed cell needing indirect addressing / extra slots |

`buffer_mutate` requires ALL of the above. Two components are demonstrated;
three remain open and each independently blocks the gate. No composition
trick within the demonstrated set produces shifting: the demonstrated
machinery is fixed-arity (2 slots, hardcoded dispatch targets), while a
buffer shift is variable-arity by definition.

## Corpus search (2026-10-11, negative)

Searched the four assigned repos for any buffer-shift / depth>2 / multi-slot
specimen: `GENEALOGIA_MALBOLGE`, `MALBOLGE-MB-DATABASE`, `MALBOLGE`,
`MalbolgeFree`/`malbolge-free` (terms: buffer shift, shift logic, memmove,
multi-slot, slot 2, depth>2, depth 3). Only binary false positives
(`*.pdb`, zig-cache hashes) and the A05_STATUS bound itself. **No specimen
exists in the corpus.**

## Validation protocol (when a specimen exists)

A specimen MUST reproduce `tests/editor_state_vectors.json` (input_hex →
`@MALPAD:` event stream incl. CHAR insert, LINE render, MOVE, backspace
delete) byte-exactly on BOTH independent witnesses — C reference runner
`runners/malbolge-original/malbolge` and `tools/oracle_classic.py` — pinned
by sha256 (LMAO output is not byte-reproducible). Generator ≠ oracle.

## Route forward (not executed this session)

1. Unblock upstream MBIR ALU chaining ("result never lands in Slot 0") —
   owned by the MB-DATABASE team, out of MALPAD scope.
2. Synthesize cursor_state (open census; bounds above give the scale floor).
3. Grow persistence past 2 slots via HeLL idioms (3-crazy reset per new cell
   + flag-budget-aware XLAT2 placement) or self-modifying address cells.
4. Only then compose a shift loop; revalidate on both interpreters.
