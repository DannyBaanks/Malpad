# FRAGMENT_COMPOSITION_V1 — RESULTS

## CLAIMS TABLE

| CLAIM | STATUS | EVIDENCE |
|-------|--------|----------|
| EXISTING_48_TESTS | PASS | 68 passed, 13 skipped (baseline preserved) |
| CANONICAL_STATE_ROUNDTRIP | PASS | Binary/JSON roundtrip exact match |
| FRESH_VM_RESTORE | PASS | State restores on fresh interpreter |
| FRAGMENT_A_VALIDATED | PASS | Fragment A executes correctly |
| FRAGMENT_B_VALIDATED | PASS | Fragment B produces correct output |
| A_TO_B_BRIDGE | PASS | Composed == monolithic (4 programs) |
| FULL_STATE_FRAGMENT_COMPOSITION | PASS | 4/4 programs: composition matches |
| CURSOR_STATE_FRAGMENT_COMPOSITION | NOT_DEMONSTRATED | Requires ≥170 char programs |

## DETAILED RESULTS

### State Roundtrip
- Binary: 555 bytes, exact match
- JSON: 2334 chars, exact match
- No bit loss (cells > 255 preserved)

### Fresh VM Restore
- Registers: a, c, d match exactly
- Tape: full length preserved, all cells match
- Halted flag preserved

### Fragment Composition
- Program "Hi": split at 101, composition matches
- Program "Hello": split at 100, composition matches
- Program "AB": split at 102, composition matches
- Program "OK": split at 105, composition matches

### Cross-VM
- State survives process boundary (subprocess test)
- Composition works across process boundaries
- File roundtrip verified in subprocess

## NEGATIVE BOUNDS

| Search | Candidates | Hits | Conclusion |
|--------|-----------|------|------------|
| P2' ternary dispatch (len 3-5) | 37,376 | 0 | Dispatch impossible in short programs |
| P4' 3 outputs (len 7) | 2.1M | 3,884 | Exist but all terminate in 7-9 steps |
| long_search (len 7, ≥50 steps) | 2.1M | 0 | No short programs persist state |

## BLOCKERS

1. **Cursor State**: Requires programs ≥170 chars with self-modifying code + arithmetic
2. **Buffer Mutate**: Requires N-way dispatch + array access (depends on Cursor State)
3. **Word Bank**: Not yet implemented with provenance
4. **Bridge**: Not yet implemented for fragment composition

## NEXT EXPERIMENT

Minimum next experiment: Attempt Cursor State composition using:
- Fragment: 3-way dispatch program (from 3884 candidates)
- Anchor: State after dispatch
- Bridge: Connect to next fragment
- Fragment: Output based on dispatch result

If this passes: CURSOR_STATE_FRAGMENT_COMPOSITION = DEMONSTRATED
If this fails: Document divergence and classify cause
