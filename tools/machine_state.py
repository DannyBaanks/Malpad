"""Canonical MachineState for Malbolge fragment composition.

Defines a versioned, deterministic, fully serializable representation of
Malbolge VM state sufficient to resume execution exactly.

This is NOT a new interpreter. It wraps the existing `malbolge` package's
MalbolgeMachine and adds serialization, hashing, and comparison primitives
needed for fragment composition.

Design principles:
- Same state → same serialization → same hash (deterministic)
- Full memory preserved (no truncation, no bit loss)
- Output is observable, not causal (stored separately from machine state)
- Version field enables format evolution without breaking old evidence
"""
from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass, field
from typing import Optional

try:
    from malbolge import MalbolgeInterpreter, MalbolgeMachine
    _MALBOLGE_AVAILABLE = True
except Exception:
    _MALBOLGE_AVAILABLE = False
    MalbolgeInterpreter = object  # type: ignore
    MalbolgeMachine = object  # type: ignore


# Malbolge Classic: 59049 cells (3^10)
MAX_CELLS = 59049

# Current schema version
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class MachineState:
    """Canonical, immutable representation of Malbolge VM state.

    This captures EVERYTHING needed to resume execution exactly:
    - Registers: a, c, d
    - Full memory: tape[0:59049] (each cell is 0..59048)
    - Execution state: halted, executed_steps
    - I/O boundary: input_consumed, output_produced
    - Provenance: program_length, fragment_id (optional)
    """
    # Registers
    a: int
    c: int
    d: int

    # Full memory (tuple for immutability/hashability)
    tape: tuple[int, ...]

    # Execution state
    halted: bool
    executed_steps: int

    # I/O boundary
    input_consumed: int  # bytes consumed from input buffer
    output_produced: bytes  # output emitted so far

    # Provenance (optional, for tracking fragments)
    program_length: int = 0
    fragment_id: str = ""

    # Schema version
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema version: {self.schema_version}")
        if len(self.tape) > MAX_CELLS:
            raise ValueError(f"Tape too long: {len(self.tape)} > {MAX_CELLS}")

    @classmethod
    def from_machine(
        cls,
        machine: MalbolgeMachine,
        executed_steps: int = 0,
        input_consumed: int = 0,
        output_produced: bytes = b"",
        program_length: int = 0,
        fragment_id: str = "",
    ) -> MachineState:
        """Create canonical state from a MalbolgeMachine instance."""
        return cls(
            a=machine.a,
            c=machine.c,
            d=machine.d,
            tape=tuple(machine.tape),
            halted=machine.halted,
            executed_steps=executed_steps,
            input_consumed=input_consumed,
            output_produced=output_produced,
            program_length=program_length,
            fragment_id=fragment_id,
        )

    def to_machine(self) -> MalbolgeMachine:
        """Restore a MalbolgeMachine from this canonical state."""
        if not _MALBOLGE_AVAILABLE:
            raise RuntimeError("malbolge package not installed")
        m = MalbolgeMachine()
        m.tape = list(self.tape)
        m.a = self.a
        m.c = self.c
        m.d = self.d
        m.halted = self.halted
        return m

    def to_bytes(self) -> bytes:
        """Deterministic binary serialization (no JSON, no pickle).

        Format (little-endian):
        - version: uint16
        - a: uint16
        - c: uint16
        - d: uint16
        - halted: uint8
        - executed_steps: uint32
        - input_consumed: uint32
        - tape_len: uint32
        - tape: uint16[tape_len]  (each cell 0..59048 fits in uint16)
        - output_len: uint32
        - output: bytes[output_len]
        - program_length: uint32
        - fragment_id_len: uint16
        - fragment_id: utf8[fragment_id_len]
        """
        parts = []
        parts.append(struct.pack("<H", self.schema_version))
        parts.append(struct.pack("<H", self.a & 0xFFFF))
        parts.append(struct.pack("<H", self.c & 0xFFFF))
        parts.append(struct.pack("<H", self.d & 0xFFFF))
        parts.append(struct.pack("<B", 1 if self.halted else 0))
        parts.append(struct.pack("<I", self.executed_steps))
        parts.append(struct.pack("<I", self.input_consumed))
        parts.append(struct.pack("<I", len(self.tape)))
        for cell in self.tape:
            parts.append(struct.pack("<H", cell & 0xFFFF))
        parts.append(struct.pack("<I", len(self.output_produced)))
        parts.append(self.output_produced)
        parts.append(struct.pack("<I", self.program_length))
        frag_bytes = self.fragment_id.encode("utf-8")
        parts.append(struct.pack("<H", len(frag_bytes)))
        parts.append(frag_bytes)
        return b"".join(parts)

    @classmethod
    def from_bytes(cls, data: bytes) -> MachineState:
        """Deserialize from binary format."""
        offset = 0

        def read(fmt, nonlocal_offset):
            size = struct.calcsize(fmt)
            val = struct.unpack_from(fmt, data, nonlocal_offset)[0]
            nonlocal_offset += size
            return val, nonlocal_offset

        version, offset = read("<H", offset)
        if version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema version: {version}")

        a, offset = read("<H", offset)
        c, offset = read("<H", offset)
        d, offset = read("<H", offset)
        halted_byte, offset = read("<B", offset)
        halted = halted_byte != 0
        executed_steps, offset = read("<I", offset)
        input_consumed, offset = read("<I", offset)

        tape_len, offset = read("<I", offset)
        tape = []
        for _ in range(tape_len):
            cell, offset = read("<H", offset)
            tape.append(cell)

        output_len, offset = read("<I", offset)
        output_produced = data[offset:offset + output_len]
        offset += output_len

        program_length, offset = read("<I", offset)
        frag_len, offset = read("<H", offset)
        fragment_id = data[offset:offset + frag_len].decode("utf-8")
        offset += frag_len

        return cls(
            a=a, c=c, d=d,
            tape=tuple(tape),
            halted=halted,
            executed_steps=executed_steps,
            input_consumed=input_consumed,
            output_produced=output_produced,
            program_length=program_length,
            fragment_id=fragment_id,
        )

    def to_json(self) -> str:
        """JSON serialization (human-readable, but larger than binary)."""
        return json.dumps({
            "schema_version": self.schema_version,
            "a": self.a,
            "c": self.c,
            "d": self.d,
            "tape": list(self.tape),
            "halted": self.halted,
            "executed_steps": self.executed_steps,
            "input_consumed": self.input_consumed,
            "output_produced": self.output_produced.hex(),
            "program_length": self.program_length,
            "fragment_id": self.fragment_id,
        }, indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> MachineState:
        """Deserialize from JSON format."""
        d = json.loads(text)
        return cls(
            a=d["a"], c=d["c"], d=d["d"],
            tape=tuple(d["tape"]),
            halted=d["halted"],
            executed_steps=d["executed_steps"],
            input_consumed=d["input_consumed"],
            output_produced=bytes.fromhex(d["output_produced"]),
            program_length=d.get("program_length", 0),
            fragment_id=d.get("fragment_id", ""),
        )

    def hash_sha256(self) -> str:
        """SHA-256 of the binary serialization."""
        return hashlib.sha256(self.to_bytes()).hexdigest()

    def hash_state_only(self) -> str:
        """SHA-256 of registers + memory only (no provenance, no I/O)."""
        state_bytes = struct.pack("<HHH", self.a, self.c, self.d)
        state_bytes += struct.pack("<B", 1 if self.halted else 0)
        for cell in self.tape:
            state_bytes += struct.pack("<H", cell & 0xFFFF)
        return hashlib.sha256(state_bytes).hexdigest()

    def __eq__(self, other: object) -> bool:
        """Exact equality: all fields must match."""
        if not isinstance(other, MachineState):
            return NotImplemented
        return (
            self.a == other.a
            and self.c == other.c
            and self.d == other.d
            and self.tape == other.tape
            and self.halted == other.halted
            and self.executed_steps == other.executed_steps
            and self.input_consumed == other.input_consumed
            and self.output_produced == other.output_produced
        )

    def diff(self, other: MachineState) -> dict:
        """Return first diverging fields between two states."""
        diffs = {}
        if self.a != other.a:
            diffs["a"] = (self.a, other.a)
        if self.c != other.c:
            diffs["c"] = (self.c, other.c)
        if self.d != other.d:
            diffs["d"] = (self.d, other.d)
        if self.halted != other.halted:
            diffs["halted"] = (self.halted, other.halted)
        if self.tape != other.tape:
            for i in range(min(len(self.tape), len(other.tape))):
                if self.tape[i] != other.tape[i]:
                    diffs[f"tape[{i}]"] = (self.tape[i], other.tape[i])
                    break
            if len(self.tape) != len(other.tape):
                diffs["tape_len"] = (len(self.tape), len(other.tape))
        if self.executed_steps != other.executed_steps:
            diffs["executed_steps"] = (self.executed_steps, other.executed_steps)
        if self.input_consumed != other.input_consumed:
            diffs["input_consumed"] = (self.input_consumed, other.input_consumed)
        if self.output_produced != other.output_produced:
            diffs["output_produced"] = (
                self.output_produced.hex(),
                other.output_produced.hex(),
            )
        return diffs
