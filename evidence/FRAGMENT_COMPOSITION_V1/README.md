# FRAGMENT_COMPOSITION_V1

## Date
2026-09-08

## Summary

Demonstrates that Malbolge programs can be composed via explicit state boundaries:
- Split a program into two fragments (A and B)
- Execute fragment A, capture machine state
- Restore state on fresh VM, execute fragment B
- Verify composed output matches monolithic execution

## Key Findings

1. **MONOLITHIC_SEARCH_WITHIN_TESTED_BOUNDS = EXHAUSTED / LOW_YIELD**
   - P2': 37,376 candidates (len 3-5), 0 hits
   - P4': 2.1M candidates (len 7), 3884 with 3 outputs but 0 with loop
   - long_search: 0 programs running ≥50 steps (len 7)

2. **SOURCE_SPLIT_COMPOSITION = REJECTED_AS_MODEL**
   - Splitting source text does not work
   - Must split at execution state boundaries

3. **CANONICAL_MACHINE_STATE = PASS**
   - Binary roundtrip: exact match
   - JSON roundtrip: exact match
   - Full memory preserved (no truncation)

4. **FRESH_VM_STATE_RESTORE = PASS**
   - State restores correctly on fresh interpreter
   - Registers (a, c, d) match exactly
   - Tape (full 59049 cells) matches exactly

5. **FRAGMENT_A_VALIDATED = PASS**
   - Fragment A executes and produces output
   - State captured at boundary is correct

6. **FRAGMENT_B_VALIDATED = PASS**
   - Fragment B executes from anchor state
   - Produces correct output

7. **A_TO_B_BRIDGE = PASS**
   - Composed output matches monolithic output
   - Tested on 4 different programs: Hi, Hello, AB, OK

8. **FULL_STATE_FRAGMENT_COMPOSITION = PASS**
   - 4/4 programs tested: composition matches monolithic
   - All registers, tape, and output match

9. **CURSOR_STATE_FRAGMENT_COMPOSITION = NOT_DEMONSTRATED**
   - Requires programs ≥170 chars with self-modifying code + arithmetic
   - Not attempted in this iteration

## Test Results

```
tests/test_fragment_epoch_transparency.py: 17 passed
tests/test_cross_vm.py: 3 passed
Total new tests: 20
Baseline: 48 passed, 12 skipped
New total: 68 passed, 13 skipped
```

## Files

- `machine_state_schema.json` - Schema definition
- `RESULTS.md` - Detailed results
- `manifest.sha256` - File hashes

## Next Steps

1. Implement Word Bank V1 with provenance
2. Implement Bridge V1 for fragment composition
3. Attempt Cursor State composition
4. Reevaluate 8 primitives
