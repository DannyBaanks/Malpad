#!/usr/bin/env python3
"""m1_sentinel_gen.py — MALPAD M1 quit-on-sentinel specimen generator.

Fuses two DEMONSTRATED MB-DATABASE idioms into one looping program:

  * mbir_dispatch_gen.py byte-VALUE dispatch (byte_dispatch18: 21/21 receipts)
  * mbir_a04_gate_gen.py loop + RESET_FLAG re-init (a04 gate: 7/7 receipts)

Spec (Classic 3^10):
    read byte B; emit B verbatim; repeat;
    B == 0x04 (QUIT sentinel) -> HALT, sentinel NOT emitted;
    EOF (a = C2 = 59048)      -> HALT.

Pipeline: base_dispatch5.hell (opcodes 00..04) -> patches:
  handlers 00..03 -> shared save_B recover+OUT (echo), like the fallback;
  handler 04      -> HALT;
  fallback        -> echo;
  echo tail + handler tails -> reset_and_loop (RESET_FLAG 3-crazy re-init of
  value, value_C1, save_tmp, save_B, carry) -> next_opcode -> IN.

Usage:
    python3 tools/m1_sentinel_gen.py src/base_dispatch5.hell -o src/m1_quit_sentinel.hell
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RESET_CELLS = "".join(
    f"RESET_FLAG{i}:\n\tNop/MovD\n\tJmp\n\n" for i in range(1, 13)
)

ECHO_BODY = (
    "\tR_MOVED\n"
    "\tROT C2 R_ROT\n"
    "\tR_FLAG11\n"
    "\tMOVED crazy_save_B\n"
)


def _sub(source: str, old: str, new: str, count: int = 1) -> str:
    n = source.count(old)
    if n != count:
        raise SystemExit(f"patch anchor not found (got {n}, want {count}): {old[:60]!r}")
    return source.replace(old, new)


def generate(source: str) -> str:
    # 1. RESET_FLAG cells in .CODE
    source = _sub(source, ".CODE\n", ".CODE\n" + RESET_CELLS, 1)

    # 2. value cell: explicit restores + RESET_FLAG1..3 (A04 idiom)
    source = _sub(
        source,
        "\tFLAG9 return_from_value_9\n",
        "\tFLAG9 return_from_value_9 R_FLAG9\n"
        "\tRESET_FLAG1 ret_rst_val_1 R_RESET_FLAG1\n"
        "\tRESET_FLAG2 ret_rst_val_2 R_RESET_FLAG2\n"
        "\tRESET_FLAG3 ret_rst_val_3\n",
    )
    # 3. value_C1 cell: R_FLAG2 restore + RESET_FLAG4..6
    source = _sub(
        source,
        "value_C1:\n\tC1\n\tFLAG2 return_from_value_C1_2\n",
        "value_C1:\n\tC1\n\tFLAG2 return_from_value_C1_2 R_FLAG2\n"
        "\tRESET_FLAG4 ret_rst_val_c1_4 R_RESET_FLAG4\n"
        "\tRESET_FLAG5 ret_rst_val_c1_5 R_RESET_FLAG5\n"
        "\tRESET_FLAG6 ret_rst_val_c1_6\n",
    )
    # 4. save_tmp cell: RESET_FLAG7..9
    source = _sub(
        source,
        "\tFLAG10 return_from_save_tmp_10 R_FLAG10\n",
        "\tFLAG10 return_from_save_tmp_10 R_FLAG10\n"
        "\tRESET_FLAG7 ret_rst_stmp_7 R_RESET_FLAG7\n"
        "\tRESET_FLAG8 ret_rst_stmp_8 R_RESET_FLAG8\n"
        "\tRESET_FLAG9 ret_rst_stmp_9\n",
    )
    # 5. save_B cell: RESET_FLAG10..12
    source = _sub(
        source,
        "\tFLAG12 return_from_save_B_12 R_FLAG12\n",
        "\tFLAG12 return_from_save_B_12 R_FLAG12\n"
        "\tRESET_FLAG10 ret_rst_sB_10 R_RESET_FLAG10\n"
        "\tRESET_FLAG11 ret_rst_sB_11 R_RESET_FLAG11\n"
        "\tRESET_FLAG12 ret_rst_sB_12\n",
    )
    # 6. carry reset return point
    source = _sub(
        source,
        "\tFLAG2 return_from_carry_2 R_FLAG2\n",
        "\tFLAG2 return_from_carry_2 R_FLAG2\n"
        "\tFLAG3 return_from_carry_reset R_FLAG3\n",
    )
    # 7. loop entry label (A04 shape: init runs once; loop target is next_opcode)
    source = _sub(
        source,
        "{\nENTRY:\n\t// IN B; value=B via value_C1 (ENTRY idiom). A ends = B.\n"
        "\tIN ?- R_IN\n",
        "{\nENTRY:\n\tMOVED next_opcode\n}{\nnext_opcode:\n\tR_MOVED\n\tIN ?- R_IN\n",
    )
    # 8. handlers 00..03 -> echo (reached via MOVED, so restore it first)
    source = _sub(source, "dispatch_00:\n\tHALT\n}{\n",
                  "dispatch_00:\n" + ECHO_BODY + "}{\n")
    for op, marker in ((1, "P"), (2, "R"), (3, "U")):
        source = _sub(
            source,
            "dispatch_%02x:\n\tROT ('%s' << 1) R_ROT\n\tOUT ?- R_OUT\n\tHALT\n}{\n"
            % (op, marker),
            "dispatch_%02x:\n" % op + ECHO_BODY + "}{\n",
        )
    # dispatch_04 stays: ROT ('L' << 1)/OUT/HALT? NO — 0x04 is the sentinel:
    source = _sub(
        source,
        "dispatch_04:\n\tROT ('L' << 1) R_ROT\n\tOUT ?- R_OUT\n\tHALT\n}{\n",
        "dispatch_04:\n\tHALT\n}{\n",
    )
    # 9. fallback echo tail: HALT -> loop
    source = _sub(
        source,
        "return_from_save_B_12:\n\tR_CRAZY R_MOVED\n\tOUT ?- R_OUT\n\tHALT\n}{\n",
        "return_from_save_B_12:\n\tR_CRAZY R_MOVED\n\tOUT ?- R_OUT\n"
        "\tMOVED reset_and_loop\n}{\n",
    )
    # 10. shared reset_and_loop block (A04 3-crazy reset: C1, C2, C0 -> C1)
    reset_block = """reset_and_loop:
\tR_MOVED
\tROT C1 R_ROT
\tR_RESET_FLAG1
\tMOVED crazy_value
}{
ret_rst_val_1:
\tR_CRAZY R_MOVED
\tROT C2 R_ROT
\tR_RESET_FLAG2
\tMOVED crazy_value
}{
ret_rst_val_2:
\tR_CRAZY R_MOVED
\tROT C0 R_ROT
\tR_RESET_FLAG3
\tMOVED crazy_value
}{
ret_rst_val_3:
\tR_CRAZY R_MOVED
\tROT C1 R_ROT
\tR_RESET_FLAG4
\tMOVED crazy_value_C1
}{
ret_rst_val_c1_4:
\tR_CRAZY R_MOVED
\tROT C2 R_ROT
\tR_RESET_FLAG5
\tMOVED crazy_value_C1
}{
ret_rst_val_c1_5:
\tR_CRAZY R_MOVED
\tROT C0 R_ROT
\tR_RESET_FLAG6
\tMOVED crazy_value_C1
}{
ret_rst_val_c1_6:
\tR_CRAZY R_MOVED
\tROT C1 R_ROT
\tR_RESET_FLAG7
\tMOVED crazy_save_tmp
}{
ret_rst_stmp_7:
\tR_CRAZY R_MOVED
\tROT C2 R_ROT
\tR_RESET_FLAG8
\tMOVED crazy_save_tmp
}{
ret_rst_stmp_8:
\tR_CRAZY R_MOVED
\tROT C0 R_ROT
\tR_RESET_FLAG9
\tMOVED crazy_save_tmp
}{
ret_rst_stmp_9:
\tR_CRAZY R_MOVED
\tROT C1 R_ROT
\tR_RESET_FLAG10
\tMOVED crazy_save_B
}{
ret_rst_sB_10:
\tR_CRAZY R_MOVED
\tROT C2 R_ROT
\tR_RESET_FLAG11
\tMOVED crazy_save_B
}{
ret_rst_sB_11:
\tR_CRAZY R_MOVED
\tROT C0 R_ROT
\tR_RESET_FLAG12
\tMOVED crazy_save_B
}{
ret_rst_sB_12:
\tR_CRAZY R_MOVED
\tROT 3 R_ROT
\tR_FLAG3
\tMOVED crazy_carry
}{
return_from_carry_reset:
\tR_CRAZY R_MOVED
\tMOVED next_opcode
}{
"""
    source = _sub(
        source,
        "return_from_increment_value_2:\n\tHALT\n}{\n",
        "return_from_increment_value_2:\n\tHALT\n}{\n" + reset_block,
    )
    return source


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path, help="base_dispatch5.hell (mbir_dispatch_gen.py --opcodes 0001020304)")
    ap.add_argument("-o", "--out", type=Path, required=True)
    a = ap.parse_args()
    out = generate(a.base.read_text(encoding="utf-8"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(out, encoding="utf-8", newline="")
    print(f"wrote {a.out} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
