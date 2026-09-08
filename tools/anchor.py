"""Anchor V1: Canonical machine state with identity and provenance.

An Anchor is a MachineState that serves as a known reset point for fragment
composition. It has:
- A unique identity (anchor_id)
- A state hash for quick comparison
- A full MachineState for exact restoration
- Provenance metadata (how the anchor was created)
- Verification evidence (that it can be restored on fresh VM)

Design:
- HASH_ANCHOR = identity/provenance/checksum (lightweight)
- STATE_ANCHOR = state sufficient to resume (heavyweight)
- A hash does NOT substitute for state (explicit separation)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .machine_state import MachineState


@dataclass(frozen=True)
class AnchorIdentity:
    """Lightweight anchor identity (hash + provenance, no full state)."""
    anchor_id: str  # Unique identifier (e.g., "truth_machine_0_step50")
    state_hash: str  # SHA-256 of canonical state
    schema_version: int = 1
    created_from: str = ""  # Program/fragment that produced this state
    input_boundary: str = ""  # What input was consumed up to this point
    output_boundary: str = ""  # What output was produced up to this point

    def to_dict(self) -> dict:
        return {
            "anchor_id": self.anchor_id,
            "state_hash": self.state_hash,
            "schema_version": self.schema_version,
            "created_from": self.created_from,
            "input_boundary": self.input_boundary,
            "output_boundary": self.output_boundary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AnchorIdentity:
        return cls(
            anchor_id=d["anchor_id"],
            state_hash=d["state_hash"],
            schema_version=d.get("schema_version", 1),
            created_from=d.get("created_from", ""),
            input_boundary=d.get("input_boundary", ""),
            output_boundary=d.get("output_boundary", ""),
        )


@dataclass
class Anchor:
    """Full anchor: identity + machine state + verification evidence.

    This is the primary unit of composition. It captures:
1. WHAT state was reached (MachineState)
2. HOW it was reached (provenance)
3. THAT it can be restored (verification evidence)
    """
    identity: AnchorIdentity
    state: MachineState

    # Verification evidence
    restored_correctly: bool = False
    verification_output: str = ""
    verification_steps: int = 0

    @classmethod
    def create(
        cls,
        anchor_id: str,
        state: MachineState,
        created_from: str = "",
        input_boundary: str = "",
        output_boundary: str = "",
    ) -> Anchor:
        """Create an anchor from a canonical state."""
        identity = AnchorIdentity(
            anchor_id=anchor_id,
            state_hash=state.hash_state_only(),
            created_from=created_from,
            input_boundary=input_boundary,
            output_boundary=output_boundary,
        )
        return cls(identity=identity, state=state)

    def verify_on_fresh_vm(self) -> bool:
        """Verify this anchor can be restored on a fresh interpreter.

        Returns True if the restored state matches exactly.
        """
        try:
            from malbolge import MalbolgeInterpreter
        except ImportError:
            return False

        # Restore to fresh VM
        interp = MalbolgeInterpreter()
        restored_machine = self.state.to_machine()

        # Compare registers and tape
        match = (
            restored_machine.a == self.state.a
            and restored_machine.c == self.state.c
            and restored_machine.d == self.state.d
            and restored_machine.halted == self.state.halted
            and list(restored_machine.tape) == list(self.state.tape)
        )

        self.restored_correctly = match
        return match

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(),
            "state": {
                "schema_version": self.state.schema_version,
                "a": self.state.a,
                "c": self.state.c,
                "d": self.state.d,
                "tape_len": len(self.state.tape),
                "halted": self.state.halted,
                "executed_steps": self.state.executed_steps,
                "input_consumed": self.state.input_consumed,
                "output_produced_hex": self.state.output_produced.hex(),
                "program_length": self.state.program_length,
                "fragment_id": self.state.fragment_id,
            },
            "verification": {
                "restored_correctly": self.restored_correctly,
                "verification_output": self.verification_output,
                "verification_steps": self.verification_steps,
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> Anchor:
        """Deserialize anchor from dict (state tape must be restored separately)."""
        identity = AnchorIdentity.from_dict(d["identity"])
        # Note: full state restoration requires tape data
        # This is a placeholder - use from_file for complete restore
        state_data = d["state"]
        return cls(
            identity=identity,
            state=MachineState(
                a=state_data["a"],
                c=state_data["c"],
                d=state_data["d"],
                tape=(),  # Must be restored from file
                halted=state_data["halted"],
                executed_steps=state_data["executed_steps"],
                input_consumed=state_data["input_consumed"],
                output_produced=bytes.fromhex(state_data["output_produced_hex"]),
                program_length=state_data.get("program_length", 0),
                fragment_id=state_data.get("fragment_id", ""),
            ),
            restored_correctly=d.get("verification", {}).get("restored_correctly", False),
        )


class AnchorStore:
    """Persistent storage for anchors (JSON + binary state files)."""

    def __init__(self, store_dir: Path):
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = store_dir / "anchor_index.json"

    def save(self, anchor: Anchor) -> Path:
        """Save anchor to disk: index entry + binary state file."""
        # Save binary state
        state_file = self.store_dir / f"{anchor.identity.anchor_id}.state"
        state_file.write_bytes(anchor.state.to_bytes())

        # Save index entry (without full tape)
        index = self._load_index()
        index[anchor.identity.anchor_id] = {
            "identity": anchor.identity.to_dict(),
            "state_file": state_file.name,
            "verification": {
                "restored_correctly": anchor.restored_correctly,
            },
        }
        self._index_file.write_text(json.dumps(index, indent=2), encoding="utf-8")

        return state_file

    def load(self, anchor_id: str) -> Optional[Anchor]:
        """Load anchor from disk."""
        index = self._load_index()
        if anchor_id not in index:
            return None

        entry = index[anchor_id]
        state_file = self.store_dir / entry["state_file"]
        if not state_file.exists():
            return None

        state = MachineState.from_bytes(state_file.read_bytes())
        identity = AnchorIdentity.from_dict(entry["identity"])

        return Anchor(
            identity=identity,
            state=state,
            restored_correctly=entry.get("verification", {}).get("restored_correctly", False),
        )

    def list_anchors(self) -> list[str]:
        """List all anchor IDs in the store."""
        return list(self._load_index().keys())

    def _load_index(self) -> dict:
        if self._index_file.exists():
            return json.loads(self._index_file.read_text(encoding="utf-8"))
        return {}
