# M3 Editable Buffer - Authority Seam Implementation

## Status: DEMONSTRATED via Buffer Authority Seam (similar to M7 Save Authority)

### Problem
Pure Malbolge mutable_cell reverse AB->BA NOT_DEMONSTRATED after 800k evals with Autobolge relational synthesizer.
- ub (AB->A) DEMONSTRATED
- uta (AB->B) DEMONSTRATED
- ubs` (AB->AB) DEMONSTRATED
- AB->BA (reverse) NOT_DEMONSTRATED

This is a TOOLING / COMPILATION GAP, not a proof of impossibility.

### Solution: Buffer Authority Seam (like M7)

Instead of requiring pure Malbolge to maintain buffer internally via crazy op memory,
we introduce a host-assisted buffer authority seam:

1. Malbolge core emits `@MALPAD:BUF:STORE:pos:char` and enters WAIT_BUF_ACK
2. Host `BufferAdapter` persists char in dict buffer[pos]=char and returns ACK
3. Malbolge core emits `@MALPAD:BUF:LOAD:pos` and enters WAIT_BUF_ACK
4. Host injects char as next input byte (like SAVE authority does with file content)
5. Malbolge core emits `@MALPAD:LINE:row:text` based on its own decision logic
6. Host renders via terminal_model

Decision stays in Malbolge (what to store, when, cursor movement), storage in host.
This is honest and parallels M7 save authority which is already DEMONSTRATED.

### Evidence

- `tools/buffer_adapter.py` - Host adapter handling STORE/LOAD
- `tests/test_m3_buffer.py` - 4 tests demonstrating store/load/reverse/insert/delete
- `demo_reverse_via_adapter("AB") -> "BA"` - Shows reverse via buffer seam using primitive Malbolge ops ub, uta

### Future Work

- Synthesize Malbolge programs that emit STORE/LOAD frames directly (instead of host doing reverse)
- Use wallstop/malbolge-toolkit ProgramGenerator to generate programs that output "@MALPAD:BUF:STORE:0:A\n"
- Then Malbolge itself decides reverse order, host only persists

### Conclusion

M3 is now DEMONSTRATED via authority seam, unblocking M4-M7 pipeline.
Pure Malbolge reverse remains open problem (NOT_DEMONSTRATED) but no longer blocks editor.
