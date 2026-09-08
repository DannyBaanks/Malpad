"""Word Bank V1: Program storage with verifiable provenance.

A Word Bank stores Malbolge programs with full provenance:
- Program source (opcodes)
- Generation method (how it was created)
- Execution results (output, state, steps)
- State anchor (for composition)
- Verification evidence (that it actually works)

Design:
- Each entry is a WordEntry with program + metadata
- Entries are indexed by output, generation method, and state hash
- Provenance is cryptographically linked (SHA-256 of program + metadata)
- State anchors are stored alongside for composition
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .anchor import Anchor, AnchorStore
from .machine_state import MachineState


@dataclass(frozen=True)
class WordProvenance:
    """Cryptographic provenance for a word entry."""
    program_hash: str  # SHA-256 of program opcodes
    generation_method: str  # How the program was created
    generation_params: dict = field(default_factory=dict)  # Parameters used
    schema_version: int = 1

    def to_dict(self) -> dict:
        return {
            "program_hash": self.program_hash,
            "generation_method": self.generation_method,
            "generation_params": self.generation_params,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WordProvenance:
        return cls(
            program_hash=d["program_hash"],
            generation_method=d["generation_method"],
            generation_params=d.get("generation_params", {}),
            schema_version=d.get("schema_version", 1),
        )


@dataclass
class WordEntry:
    """A single word in the bank: program + provenance + execution results."""
    program: str  # The Malbolge program (opcodes)
    provenance: WordProvenance
    output: str = ""  # What the program outputs
    state: Optional[MachineState] = None  # Final state (if captured)
    anchor: Optional[Anchor] = None  # Composition anchor (if created)
    executed_steps: int = 0  # Steps to produce output
    input_used: str = ""  # Input consumed

    @classmethod
    def create(
        cls,
        program: str,
        generation_method: str,
        generation_params: Optional[dict] = None,
        output: str = "",
        state: Optional[MachineState] = None,
        executed_steps: int = 0,
        input_used: str = "",
    ) -> WordEntry:
        """Create a new word entry with provenance."""
        program_hash = hashlib.sha256(program.encode()).hexdigest()
        provenance = WordProvenance(
            program_hash=program_hash,
            generation_method=generation_method,
            generation_params=generation_params or {},
        )
        return cls(
            program=program,
            provenance=provenance,
            output=output,
            state=state,
            executed_steps=executed_steps,
            input_used=input_used,
        )

    def to_dict(self) -> dict:
        result = {
            "program": self.program,
            "provenance": self.provenance.to_dict(),
            "output": self.output,
            "executed_steps": self.executed_steps,
            "input_used": self.input_used,
        }
        if self.anchor:
            result["anchor"] = self.anchor.to_dict()
        return result

    @classmethod
    def from_dict(cls, d: dict) -> WordEntry:
        provenance = WordProvenance.from_dict(d["provenance"])
        anchor = None
        if "anchor" in d:
            anchor = Anchor.from_dict(d["anchor"])
        return cls(
            program=d["program"],
            provenance=provenance,
            output=d.get("output", ""),
            anchor=anchor,
            executed_steps=d.get("executed_steps", 0),
            input_used=d.get("input_used", ""),
        )


class WordBank:
    """Persistent storage for word entries with provenance tracking."""

    def __init__(self, bank_dir: Path):
        self.bank_dir = bank_dir
        self.bank_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = bank_dir / "word_index.json"
        self._anchor_store = AnchorStore(bank_dir / "anchors")

    def add(self, entry: WordEntry) -> str:
        """Add a word entry to the bank. Returns the entry ID."""
        # Generate entry ID from program hash
        entry_id = entry.provenance.program_hash[:16]

        # Save anchor if present
        if entry.anchor:
            self._anchor_store.save(entry.anchor)

        # Save state if present
        if entry.state:
            state_file = self.bank_dir / f"{entry_id}.state"
            state_file.write_bytes(entry.state.to_bytes())

        # Update index
        index = self._load_index()
        index[entry_id] = {
            "provenance": entry.provenance.to_dict(),
            "output": entry.output,
            "executed_steps": entry.executed_steps,
            "input_used": entry.input_used,
            "has_anchor": entry.anchor is not None,
            "has_state": entry.state is not None,
        }
        self._index_file.write_text(json.dumps(index, indent=2), encoding="utf-8")

        # Save program file
        program_file = self.bank_dir / f"{entry_id}.mal"
        program_file.write_text(entry.program, encoding="utf-8")

        return entry_id

    def get(self, entry_id: str) -> Optional[WordEntry]:
        """Retrieve a word entry by ID."""
        index = self._load_index()
        if entry_id not in index:
            return None

        entry_data = index[entry_id]
        program_file = self.bank_dir / f"{entry_id}.mal"
        if not program_file.exists():
            return None

        program = program_file.read_text(encoding="utf-8")
        provenance = WordProvenance.from_dict(entry_data["provenance"])

        anchor = None
        if entry_data.get("has_anchor"):
            anchor = self._anchor_store.load(entry_id)

        state = None
        if entry_data.get("has_state"):
            state_file = self.bank_dir / f"{entry_id}.state"
            if state_file.exists():
                state = MachineState.from_bytes(state_file.read_bytes())

        return WordEntry(
            program=program,
            provenance=provenance,
            output=entry_data.get("output", ""),
            state=state,
            anchor=anchor,
            executed_steps=entry_data.get("executed_steps", 0),
            input_used=entry_data.get("input_used", ""),
        )

    def find_by_output(self, output: str) -> list[str]:
        """Find all entry IDs that produce the given output."""
        index = self._load_index()
        return [
            eid for eid, data in index.items()
            if data.get("output") == output
        ]

    def find_by_method(self, method: str) -> list[str]:
        """Find all entry IDs created by the given method."""
        index = self._load_index()
        return [
            eid for eid, data in index.items()
            if data.get("provenance", {}).get("generation_method") == method
        ]

    def list_entries(self) -> list[str]:
        """List all entry IDs in the bank."""
        return list(self._load_index().keys())

    def verify_entry(self, entry_id: str) -> dict:
        """Verify a word entry's integrity and provenance."""
        entry = self.get(entry_id)
        if entry is None:
            return {"valid": False, "error": "Entry not found"}

        # Verify program hash
        actual_hash = hashlib.sha256(entry.program.encode()).hexdigest()
        if actual_hash != entry.provenance.program_hash:
            return {"valid": False, "error": "Program hash mismatch"}

        # Verify anchor if present
        anchor_ok = True
        if entry.anchor:
            anchor_ok = entry.anchor.verify_on_fresh_vm()

        return {
            "valid": True,
            "program_hash_ok": True,
            "anchor_ok": anchor_ok,
            "output": entry.output,
            "method": entry.provenance.generation_method,
        }

    def _load_index(self) -> dict:
        if self._index_file.exists():
            return json.loads(self._index_file.read_text(encoding="utf-8"))
        return {}
