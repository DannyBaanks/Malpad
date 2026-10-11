# MALPAD — M3 gate evidence

Date: 2026-08-30. Milestone: **M3 (single-line editable buffer in Malbolge)**.

## Gate: `EDITABLE_BUFFER_DEMONSTRATED`

**Status: NOT_DEMONSTRATED.**

This is the acknowledged hard wall (roadmap §8/§9, and the risk flagged since
the project start). It is reported honestly, not papered over.

## What M3 requires (from the frozen editor IR)

A single Malbolge program that maintains, across loop iterations:
- a persistent **buffer** (fixed ASCII, up to 80);
- a persistent **cursor**;
- and dispatches on input into ~6 actions: printable→insert, LEFT, RIGHT,
  BACKSPACE, (SAVE), QUIT — mutating the buffer/cursor accordingly.

## Why it is NOT_DEMONSTRATED

| Requirement | Status |
|-------------|--------|
| input-branching decision | DEMONSTRATED (M2 truth-machine) |
| persistent mutable state (buffer/cursor) driven by input | **NOT DEMONSTRATED** |
| multi-way (~6) input dispatch | NOT DEMONSTRATED |
| Malbolge program reproducing `tests/editor_state_vectors.json` | NOT DEMONSTRATED |

Reason (precise, not a shortcut):
1. **No existing stateful input-branching Malbolge program was found.** The
   ecosystem (malbolge-rs programs, esolangs corpus, E31-A, our own M1 cat) has
   echo/cat/hello/99bottles/quine/truth-machine — no counter/register-mutating
   editor-like program to source or adapt.
2. **No generator/compiler exists for stateful input-branching Malbolge.** The
   `malbolge-generator` produces text-output programs (print fixed strings), not
   mutable state machines driven by runtime input.
3. **Hand-writing it is beyond practical reach.** A single-line editor core in
   Malbolge is a large, low-level, self-modifying program; producing and
   debugging one correctly in a session is not realistic, and a wrong program
   would be indistinguishable from an untested one.

## The concrete path (what would close M3)

The roadmap §8/§9 strategy: **build an IR→Malbolge compiler** that turns the
frozen editor state machine (`tools/editor_ir.py` + `editor_state_vectors.json`)
into a Malbolge specimen. Constraints:
- `generator != oracle`: the specimen is validated on independent interpreters,
  never by its own generator.
- Output must reproduce the `editor_state_vectors.json` vectors cross-backend.
- This is a **multi-session sub-project** (essentially writing a Malbolge
  compiler for a small stateful IR), not a single-step task.

## Evidence for the wall

- M2 truth-machine: `evidence/m2_state/truth_machine.mal` (the only
  input-branching program verified cross-backend; proves decision, not buffer).
- Ecosystem inventory: malbolge-rs programs = echo/cat/hello/99bottles only.
- Frozen target: `tests/editor_state_vectors.json` (8 vectors the specimen must
  reproduce).

## Verdict

`EDITABLE_BUFFER_DEMONSTRATED` = **NOT_DEMONSTRATED**. M3 is gated on the
IR→Malbolge compiler. No claim is made that the editor logic runs in Malbolge
yet; the frozen IR + vectors stand as the specification and validation target.
## Correction (append, 2026-10-11)

Raw history above preserved. Updates to the requirement table, per component,
from this session's cross-checks (generator ≠ oracle; all on C reference +
`tools/oracle_classic.py`):

| Requirement | 2026-08-30 status | 2026-10-11 status |
|---|---|---|
| input-branching decision | DEMONSTRATED (M2 truth-machine) | unchanged |
| persistent mutable state (buffer/cursor) driven by input | NOT_DEMONSTRATED | **partial**: 2-slot persistence DEMONSTRATED via A05b LIFO (`evidence/mutable_cell_reverse`, 7/7); cursor_state and depth>2 still NOT_DEMONSTRATED (see below) |
| multi-way (~6) input dispatch | NOT_DEMONSTRATED | **DEMONSTRATED by lineage**: `byte_dispatch18` 21/21 (MB-DATABASE) + MALPAD fusion `m1_quit_sentinel` 6-way + sentinel, 5/5 two interpreters |
| Malbolge program reproducing `tests/editor_state_vectors.json` | NOT_DEMONSTRATED | **still NOT_DEMONSTRATED** — the full vectors need cursor_state + shifting, both open |

The hardest remaining component is `buffer_mutate` (insert/delete with
data-dependent shifting). Its precise dependency chain and the new exhaustive
bounds are recorded in `evidence/buffer_mutate/GATES.md` (2026-10-11).

**Verdict update**: `EDITABLE_BUFFER_DEMONSTRATED` (a single Malbolge program
reproducing the frozen vectors end-to-end) = **still NOT_DEMONSTRATED**. What
changed is that two of its constituent primitives (N-way dispatch, 2-slot
persistent store/load incl. AB→BA reverse) moved from open to DEMONSTRATED,
narrowing the gap to cursor_state + depth>2 + shifting. No upgrade of the
overall M3 verdict is claimed without a real specimen.
