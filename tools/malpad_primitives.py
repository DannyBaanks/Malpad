#!/usr/bin/env python3
"""MALPAD primitives: per-character Malbolge synthesis with a reusable bank.

Idea (MALPAD primitives v1):
    H O L A = H-delta . O-delta . L-delta . A-delta + halt
Each character is synthesized as an opcodes DELTA that runs from the current
machine state and prints exactly that character. Deltas are cached in a
persistent bank keyed by (machine_state_hash, char), so repeated contexts
cost 0 synthesis.

Demonstrated properties (see evidence/malpad_primitives/GATES.md):
  - composition is REAL: one program, one console, exact concatenated output
  - byte-exact output vs requested text (verified by canonical execution)
  - bank reuse: second run of the same text does zero re-synthesis

Deliberately NOT claimed:
  - anchor-reset composition (bridge machinery in the translator is broken;
    measured 2026-09-04: anchor.bridge() silently returns empty ops)
  - any claim that scaling is sub-linear; cost is per (state, char) pair

Dependency: the `malbolge` package (malbolge-generator, MIT). No part of the
translator package is imported: the search loop below is 30 lines and lives
here, standalone, under MALPAD's own tests.

Usage:
    py tools/malpad_primitives.py "HOLA MUNDO" --execute
    py tools/malpad_primitives.py --warmup ascii --execute
"""
from __future__ import annotations

import argparse
import hashlib
import json
import string
import sys
import time
from pathlib import Path

from malbolge import GenerationConfig, MalbolgeInterpreter, ProgramGenerator
from malbolge.generator import _GenerationStats, _PrefixState

BOOTSTRAP = "i" + "o" * 99  # canonical bootstrap (verified 2026-09-04)
HALT = "v"

DEFAULT_BANK = (
    Path(__file__).resolve().parent.parent
    / "evidence" / "malpad_primitives" / "primitive_bank.json"
)
PACKS_DIR = (
    Path(__file__).resolve().parent.parent
    / "evidence" / "malpad_primitives" / "packs"
)

# ---------------------------------------------------------------------------
# Language packs (starter alphabets; grow them by composing, not by editing):
# every entry is independently verified: program from bootstrap -> execute ->
# bytes == utf8(char). See evidence/malpad_primitives/packs/<lang>/receipts.
# ---------------------------------------------------------------------------

PACKS = {
    "ascii": "ascii",
    "es": "es",
    "ja": "ja",
    "zh": "zh",
}


def pack_chars(pack: str) -> list[str]:
    if pack == "ascii":
        return [chr(c) for c in list(range(32, 127)) + [9, 10]]
    if pack == "es":
        return list("áéíóúüñÁÉÍÓÚÜÑ¡¿«»")
    if pack == "ja":
        chars = [chr(c) for c in range(0x3041, 0x3097)]   # hiragana ぁ..ゖ
        chars += [chr(c) for c in range(0x30A1, 0x30FB)]  # katakana ァ..ヺ
        chars += list("ー・。「」、〜")
        return chars
    if pack == "zh":
        return list("的一是不了人我在有他这中大来上国个到说们为子"
                    "和你地出道也时年得就那要下以生会自着去之过家学"
                    "对可她里后小么心多天而能好都然没日于起还一发成"
                    "事只作当想看文无开手十用主行方又如前所本见经头"
                    "面公同三已老从动两长知民样样现")
    raise ValueError(f"unknown pack {pack!r}; choose from {sorted(PACKS)}")


def build_pack(composer: "PrimitiveComposer", pack: str,
               out_root: Path = PACKS_DIR) -> dict:
    """Synthesize+verify one program per char of the pack, from bootstrap."""
    out_dir = out_root / pack
    out_dir.mkdir(parents=True, exist_ok=True)
    receipts = []
    t0 = time.time()
    for ch in pack_chars(pack):
        tb = ch.encode("utf-8")
        delta = composer._synth_delta(composer.boot_machine, BOOTSTRAP,
                                      composer._target_bytes(tb))
        program = BOOTSTRAP + delta + HALT
        r = composer.execute(program, expect_bytes=tb)
        ok = r["byte_exact"] and r["halt_reason"] == "halt_opcode"
        prog_name = f"U+{ord(ch):04X}.mal"
        (out_dir / prog_name).write_text(program, encoding="ascii", newline="")
        receipts.append({
            "char": ch,
            "codepoint": f"U+{ord(ch):04X}",
            "utf8_bytes": tb.hex(),
            "program_file": prog_name,
            "program_sha256": hashlib.sha256(program.encode("ascii")).hexdigest(),
            "program_ops": len(program),
            "steps": r["steps"],
            "halt_reason": r["halt_reason"],
            "byte_exact": r["byte_exact"],
            "verified": bool(ok),
        })
        print(f"  [{pack}] {ch} U+{ord(ch):04X} ops={len(program)} "
              f"exact={r['byte_exact']}", flush=True)
    summary = {
        "pack": pack,
        "chars": len(receipts),
        "verified": sum(1 for r in receipts if r["verified"]),
        "seconds": round(time.time() - t0, 1),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out_dir / "receipts.json").write_text(
        json.dumps({"summary": summary, "receipts": receipts}, indent=1,
                   ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[{pack}] {summary['verified']}/{summary['chars']} verified, "
          f"{summary['seconds']}s -> {out_dir}")
    return summary


def state_hash(machine) -> str:
    # tape cells are ternary values (may exceed 255); hash their int tuple
    head = ",".join(str(v) for v in machine.tape[:100])
    return hashlib.md5(
        f"{machine.a},{machine.c},{machine.d},{head}".encode()
    ).hexdigest()


class PrimitiveBank:
    """(state_hash, char) -> opcodes delta, persisted as JSON."""

    def __init__(self, path: Path):
        self.path = path
        self._entries: dict[str, str] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            self._entries = {e["key"]: e["delta"] for e in raw["entries"]}

    def get(self, key: str) -> str | None:
        return self._entries.get(key)

    def put(self, key: str, delta: str) -> None:
        self._entries[key] = delta

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "malpad-primitive-bank/v1",
            "entries": [
                {"key": k, "delta": v} for k, v in sorted(self._entries.items())
            ],
        }
        self.path.write_text(json.dumps(payload, indent=0) + "\n", encoding="utf-8")

    def __len__(self) -> int:
        return len(self._entries)


class PrimitiveComposer:
    def __init__(self, max_search_depth: int = 5, seed: int = 42):
        self.generator = ProgramGenerator()
        self.interp = MalbolgeInterpreter()
        self.depth = max_search_depth
        self.seed = seed
        boot = self.interp.execute(BOOTSTRAP, capture_machine=True)
        assert boot.machine is not None, "bootstrap failed"
        self.boot_machine = boot.machine

    def _synth_delta(self, machine, prefix_ops: str, target: str) -> str:
        """Search opcodes that extend prefix so output gains exactly `target`."""
        cfg = GenerationConfig(opcode_choices="op*",
                               max_search_depth=self.depth,
                               random_seed=self.seed)
        stats = _GenerationStats()
        cache: dict = {}
        dead: set = set()
        cur = _PrefixState(opcodes=prefix_ops, output="", machine=machine.copy())
        for idx in range(len(target)):
            tpref = target[: idx + 1]
            found = False
            combos = list(cfg.opcode_choices)
            depth = 0
            while not found:
                depth += 1
                for cand in combos:
                    suf = cand + "<"
                    if cur.opcodes + suf in dead:
                        continue
                    cs, _ = self.generator._get_or_extend_state(
                        cur, suf, self.interp, cfg, cache, stats)
                    if cs.machine is None:
                        continue
                    out = cs.output
                    if target.startswith(out) and len(out) <= len(target) \
                            and out == tpref:
                        cur = cs
                        found = True
                        break
                if found:
                    break
                combos = [b + o for b in combos for o in cfg.opcode_choices
                          if (cur.opcodes + b + o + "<") not in dead]
                if not combos:
                    raise RuntimeError(f"search exhausted at {tpref!r}")
                if depth >= cfg.max_search_depth:
                    viable = [c for c in combos
                              if (cur.opcodes + c + "<") not in dead]
                    if not viable:
                        combos = list(cfg.opcode_choices)
                        depth = 0
                        continue
                    rs, _ = self.generator._get_or_extend_state(
                        cur, viable[0], self.interp, cfg, cache, stats)
                    if rs.machine is None:
                        continue
                    cur = rs
                    combos = list(cfg.opcode_choices)
                    depth = 0
        return cur.opcodes[len(prefix_ops):]

    # ------------------------------------------------------------------
    # v2: byte-domain primitives + character tokens (UTF-8 packs)
    # ------------------------------------------------------------------

    def _target_bytes(self, token_bytes: bytes) -> str:
        """The interpreter captures output as a str with latin-1 byte values."""
        return token_bytes.decode("latin-1")

    def compose_token(self, token_bytes: bytes, bank: PrimitiveBank,
                      machine, program: str) -> tuple:
        """Synthesize-or-reuse a delta emitting exactly token_bytes.
        Returns (machine, program, stats_delta)."""
        key = f"{state_hash(machine)}:{token_bytes.hex()}"
        delta = bank.get(key)
        if delta is None:
            t0 = time.time()
            delta = self._synth_delta(machine, program,
                                      self._target_bytes(token_bytes))
            secs = time.time() - t0
            bank.put(key, delta)
            synthesized = 1
        else:
            secs = 0.0
            synthesized = 0
        r = self.interp.execute_from_snapshot(machine, delta,
                                              capture_machine=True)
        if r.machine is None or r.output != self._target_bytes(token_bytes):
            raise RuntimeError(
                f"delta for {token_bytes.hex()} mis-behaved: "
                f"output={r.output.encode('latin-1').hex()!r}")
        return r.machine, program + delta, synthesized, secs

    def compose_bytes(self, data: bytes, bank: PrimitiveBank) -> dict:
        """Compose per single-byte tokens."""
        machine = self.boot_machine
        program = BOOTSTRAP
        stats = {"synthesized": 0, "bank_hits": 0, "synth_seconds": 0.0}
        for b in bytes(data):
            machine, program, synthesized, secs = self.compose_token(
                bytes([b]), bank, machine, program)
            stats["synthesized"] += synthesized
            stats["bank_hits"] += (1 - synthesized)
            stats["synth_seconds"] += secs
        return {"program": program + HALT, "ops": len(program) + 1,
                "stats": stats}

    def compose(self, text: str, bank: PrimitiveBank) -> dict:
        """Compose text with char-level tokens when present in the bank,
        byte-level tokens otherwise. Output must equal utf-8(text) bytes."""
        machine = self.boot_machine
        program = BOOTSTRAP
        stats = {"synthesized": 0, "bank_hits": 0, "synth_seconds": 0.0,
                 "char_tokens": 0, "byte_tokens": 0}
        # first pass: which chars does the bank know at THIS state path?
        # (state evolves as we go, so we simply probe during the loop)
        for ch in text:
            token = ch.encode("utf-8")
            key = f"{state_hash(machine)}:{token.hex()}"
            if bank.get(key) is not None:
                machine, program, synthesized, secs = self.compose_token(
                    token, bank, machine, program)
                stats["char_tokens"] += 1
                stats["synthesized"] += synthesized
                stats["bank_hits"] += (1 - synthesized)
                stats["synth_seconds"] += secs
            else:
                for b in token:
                    machine, program, synthesized, secs = self.compose_token(
                        bytes([b]), bank, machine, program)
                    stats["byte_tokens"] += 1
                    stats["synthesized"] += synthesized
                    stats["bank_hits"] += (1 - synthesized)
                    stats["synth_seconds"] += secs
        return {"program": program + HALT, "ops": len(program) + 1,
                "stats": stats}

    def execute(self, program: str, expect_bytes: bytes | None = None) -> dict:
        r = self.interp.execute(program, capture_machine=True)
        out_bytes = r.output.encode("latin-1")
        res = {"output_bytes_hex": out_bytes.hex(),
               "halt_reason": r.halt_reason, "steps": r.steps}
        if expect_bytes is not None:
            res["byte_exact"] = out_bytes == expect_bytes
        return res


def main() -> int:
    ap = argparse.ArgumentParser(description="MALPAD per-token primitives")
    ap.add_argument("text", nargs="?", help="UTF-8 text to compose")
    ap.add_argument("--warmup", choices=sorted(PACKS),
                    help="compose the pack's chars in sequence (bank exercise)")
    ap.add_argument("--build-pack", choices=sorted(PACKS),
                    help="emit evidence packs: one verified .mal per char")
    ap.add_argument("--text-file", type=Path,
                    help="read UTF-8 text from file (shell-proof for unicode)")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    ap.add_argument("--depth", type=int, default=5)
    ap.add_argument("--output", type=Path, help="write .mal program")
    args = ap.parse_args()

    composer = PrimitiveComposer(max_search_depth=args.depth)

    if args.build_pack:
        summary = build_pack(composer, args.build_pack)
        return 0 if summary["verified"] == summary["chars"] else 1

    text = args.text
    if args.text_file:
        text = args.text_file.read_text(encoding="utf-8")
    if args.warmup:
        text = "".join(pack_chars(args.warmup))
    if text is None:
        ap.error("need text, --text-file, --warmup or --build-pack")

    expect = text.encode("utf-8")
    bank = PrimitiveBank(args.bank)
    t0 = time.time()
    res = composer.compose(text, bank)
    bank.save()
    stats = res["stats"]

    print(f"text_chars: {len(text)}  utf8_bytes: {len(expect)}")
    print(f"program_ops: {res['ops']}")
    print(f"char_tokens: {stats.get('char_tokens', 0)}  "
          f"byte_tokens: {stats.get('byte_tokens', 0)}")
    print(f"synthesized_now: {stats['synthesized']}")
    print(f"bank_hits: {stats['bank_hits']}")
    print(f"bank_size: {len(bank)}")
    print(f"synth_seconds: {stats['synth_seconds']:.2f}")
    print(f"total_seconds: {time.time() - t0:.2f}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(res["program"], encoding="ascii", newline="")

    if args.execute:
        r = composer.execute(res["program"], expect_bytes=expect)
        print(f"execution: halt={r['halt_reason']} steps={r['steps']}")
        print(f"byte_exact: {r['byte_exact']}")
        if not r["byte_exact"]:
            print(f"got:  {r['output_bytes_hex']}")
            print(f"want: {expect.hex()}")
        return 0 if r["byte_exact"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
