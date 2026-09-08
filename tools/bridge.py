"""Bridge V1: Explicit postcondition → precondition composition.

A Bridge connects two fragments:
- Fragment A: produces a postcondition (state + output)
- Fragment B: requires a precondition (state + input)

The Bridge verifies that:
1. Fragment A's postcondition satisfies Fragment B's precondition
2. The composition produces the expected output
3. State transitions are valid

Design:
- Precondition: what the VM state must look like before fragment B
- Postcondition: what the VM state looks like after fragment A
- Bridge verification: postcondition satisfies precondition
- Composition: fragment A → bridge → fragment B
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .anchor import Anchor
from .machine_state import MachineState


@dataclass(frozen=True)
class Postcondition:
    """What fragment A produces: state + output."""
    state: MachineState
    output_produced: str = ""
    steps_executed: int = 0

    def to_dict(self) -> dict:
        return {
            "state_hash": self.state.hash_sha256(),
            "output_produced": self.output_produced,
            "steps_executed": self.steps_executed,
            "halted": self.state.halted,
        }


@dataclass(frozen=True)
class Precondition:
    """What fragment B requires: state + input."""
    state_hash: str  # Expected state hash (can be partial)
    input_required: str = ""  # Input fragment B needs
    halted_ok: bool = False  # Whether halted state is acceptable

    def to_dict(self) -> dict:
        return {
            "state_hash": self.state_hash,
            "input_required": self.input_required,
            "halted_ok": self.halted_ok,
        }


@dataclass
class BridgeResult:
    """Result of bridging two fragments."""
    success: bool
    postcondition: Postcondition
    precondition: Precondition
    composed_output: str = ""
    composed_steps: int = 0
    verification_error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "postcondition": self.postcondition.to_dict(),
            "precondition": self.precondition.to_dict(),
            "composed_output": self.composed_output,
            "composed_steps": self.composed_steps,
            "verification_error": self.verification_error,
        }


class Bridge:
    """Verify and compose fragments via postcondition → precondition."""

    @staticmethod
    def verify(
        postcondition: Postcondition,
        precondition: Precondition,
    ) -> tuple[bool, str]:
        """Verify that postcondition satisfies precondition.

        Returns (ok, error_message).
        """
        # Check state hash
        if postcondition.state.hash_sha256() != precondition.state_hash:
            return False, "State hash mismatch"

        # Check halted status
        if postcondition.state.halted and not precondition.halted_ok:
            return False, "Fragment A halted but precondition requires running"

        return True, ""

    @staticmethod
    def compose(
        fragment_a: str,
        fragment_b: str,
        input_data: str = "",
        max_steps: int = 10000,
    ) -> BridgeResult:
        """Compose two fragments via bridge verification.

        1. Execute fragment A
        2. Capture postcondition
        3. Create precondition for fragment B
        4. Verify postcondition satisfies precondition
        5. Execute fragment B from postcondition state
        6. Return composed output
        """
        from malbolge import MalbolgeInterpreter

        # Execute fragment A
        interp_a = MalbolgeInterpreter()
        result_a = interp_a.execute(
            fragment_a,
            input_buffer=input_data,
            max_steps=max_steps,
            capture_machine=True,
        )

        # Capture postcondition
        state_a = MachineState.from_machine(
            result_a.machine,
            executed_steps=result_a.steps,
            output_produced=result_a.output.encode(),
        )
        postcondition = Postcondition(
            state=state_a,
            output_produced=result_a.output,
            steps_executed=result_a.steps,
        )

        # Create precondition for fragment B
        precondition = Precondition(
            state_hash=state_a.hash_sha256(),
            input_required="",
            halted_ok=False,
        )

        # Verify bridge
        ok, error = Bridge.verify(postcondition, precondition)
        if not ok:
            return BridgeResult(
                success=False,
                postcondition=postcondition,
                precondition=precondition,
                verification_error=error,
            )

        # Execute fragment B from postcondition state
        interp_b = MalbolgeInterpreter()
        result_b = interp_b.execute_from_snapshot(
            state_a.to_machine(),
            fragment_b,
            max_steps=max_steps,
        )

        composed_output = postcondition.output_produced + result_b.output
        composed_steps = postcondition.steps_executed + result_b.steps

        return BridgeResult(
            success=True,
            postcondition=postcondition,
            precondition=precondition,
            composed_output=composed_output,
            composed_steps=composed_steps,
        )

    @staticmethod
    def compose_with_anchor(
        anchor: Anchor,
        fragment_b: str,
        max_steps: int = 10000,
    ) -> BridgeResult:
        """Compose from an existing anchor (skips fragment A execution)."""
        from malbolge import MalbolgeInterpreter

        # Create postcondition from anchor
        postcondition = Postcondition(
            state=anchor.state,
            output_produced=anchor.identity.output_boundary,
            steps_executed=0,
        )

        # Create precondition
        precondition = Precondition(
            state_hash=anchor.identity.state_hash,
            input_required="",
            halted_ok=False,
        )

        # Verify bridge
        ok, error = Bridge.verify(postcondition, precondition)
        if not ok:
            return BridgeResult(
                success=False,
                postcondition=postcondition,
                precondition=precondition,
                verification_error=error,
            )

        # Execute fragment B
        interp_b = MalbolgeInterpreter()
        result_b = interp_b.execute_from_snapshot(
            anchor.state.to_machine(),
            fragment_b,
            max_steps=max_steps,
        )

        composed_output = postcondition.output_produced + result_b.output
        composed_steps = result_b.steps

        return BridgeResult(
            success=True,
            postcondition=postcondition,
            precondition=precondition,
            composed_output=composed_output,
            composed_steps=composed_steps,
        )
