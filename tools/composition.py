"""Fragment Composition Experiment V1.

Demonstrates: FULL_STATE_FRAGMENT_COMPOSITION_V1

Split a Malbolge program into two fragments (A and B), execute them separately
with a canonical state boundary, and verify the composed output matches the
monolithic execution.

This is NOT source splitting. This is execution state splitting:
  S0 -- execute fragment A --> S1 -- snapshot --> ANCHOR(S1)
  -- fresh VM --> RESTORE(S1) -- execute fragment B --> S2

And verify: S2 == S2_reference (full monolithic run)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from malbolge import MalbolgeInterpreter, MalbolgeMachine, normalize, StepLimitExceededError, MalbolgeRuntimeError

from .machine_state import MachineState
from .anchor import Anchor, AnchorStore


@dataclass
class CompositionResult:
    """Result of a fragment composition experiment."""
    program_name: str
    program_length: int
    split_at: int

    # Monolithic reference
    full_output: str
    full_steps: int
    full_halted: bool

    # Fragment A
    fragment_a_output: str
    fragment_a_steps: int
    anchor_state_hash: str

    # Fragment B (fresh VM)
    fragment_b_output: str
    fragment_b_steps: int
    fragment_b_halted: bool

    # Composition
    composed_output: str
    composition_match: bool

    # State comparison
    anchor_register_match: bool
    anchor_tape_match: bool

    # Evidence
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "program_name": self.program_name,
            "program_length": self.program_length,
            "split_at": self.split_at,
            "full_output": self.full_output,
            "full_steps": self.full_steps,
            "full_halted": self.full_halted,
            "fragment_a_output": self.fragment_a_output,
            "fragment_a_steps": self.fragment_a_steps,
            "anchor_state_hash": self.anchor_state_hash,
            "fragment_b_output": self.fragment_b_output,
            "fragment_b_steps": self.fragment_b_steps,
            "fragment_b_halted": self.fragment_b_halted,
            "composed_output": self.composed_output,
            "composition_match": self.composition_match,
            "anchor_register_match": self.anchor_register_match,
            "anchor_tape_match": self.anchor_tape_match,
            "error": self.error,
        }


def run_composition_experiment(
    opcodes: str,
    input_data: str,
    program_name: str = "unknown",
    split_at: Optional[int] = None,
    max_steps: int = 5000,
) -> CompositionResult:
    """Run a fragment composition experiment.

    1. Execute full program (reference)
    2. Execute fragment A (prefix) on VM1, capture state
    3. Create anchor from captured state
    4. Execute fragment B (suffix) on fresh VM2, starting from anchor state
    5. Compare composed output to reference
    """
    if split_at is None:
        split_at = len(opcodes) // 2

    if split_at <= 0 or split_at >= len(opcodes):
        return CompositionResult(
            program_name=program_name,
            program_length=len(opcodes),
            split_at=split_at,
            full_output="", full_steps=0, full_halted=False,
            fragment_a_output="", fragment_a_steps=0, anchor_state_hash="",
            fragment_b_output="", fragment_b_steps=0, fragment_b_halted=False,
            composed_output="", composition_match=False,
            anchor_register_match=False, anchor_tape_match=False,
            error="Invalid split_at",
        )

    fragment_a = opcodes[:split_at]
    fragment_b = opcodes[split_at:]

    # 1. Monolithic reference
    try:
        interp_full = MalbolgeInterpreter()
        result_full = interp_full.execute(
            opcodes,
            input_buffer=iter(input_data),
            max_steps=max_steps,
            capture_machine=True,
        )
        full_output = result_full.output
        full_steps = result_full.steps
        full_halted = result_full.machine.halted
    except (StepLimitExceededError, MalbolgeRuntimeError) as e:
        return CompositionResult(
            program_name=program_name,
            program_length=len(opcodes),
            split_at=split_at,
            full_output="", full_steps=0, full_halted=False,
            fragment_a_output="", fragment_a_steps=0, anchor_state_hash="",
            fragment_b_output="", fragment_b_steps=0, fragment_b_halted=False,
            composed_output="", composition_match=False,
            anchor_register_match=False, anchor_tape_match=False,
            error=f"Full run failed: {e}",
        )

    # 2. Fragment A on VM1
    try:
        interp_a = MalbolgeInterpreter()
        result_a = interp_a.execute(
            fragment_a,
            input_buffer=iter(input_data),
            max_steps=max_steps,
            capture_machine=True,
        )
    except (StepLimitExceededError, MalbolgeRuntimeError) as e:
        return CompositionResult(
            program_name=program_name,
            program_length=len(opcodes),
            split_at=split_at,
            full_output=full_output, full_steps=full_steps, full_halted=full_halted,
            fragment_a_output="", fragment_a_steps=0, anchor_state_hash="",
            fragment_b_output="", fragment_b_steps=0, fragment_b_halted=False,
            composed_output="", composition_match=False,
            anchor_register_match=False, anchor_tape_match=False,
            error=f"Fragment A failed: {e}",
        )

    # 3. Create anchor
    anchor_state = MachineState.from_machine(
        result_a.machine,
        executed_steps=result_a.steps,
        input_consumed=len(input_data) if len(result_a.output) > 0 else 0,
        output_produced=result_a.output.encode(),
        program_length=len(fragment_a),
        fragment_id=f"{program_name}_A",
    )
    anchor = Anchor.create(
        anchor_id=f"{program_name}_split{split_at}",
        state=anchor_state,
        created_from=program_name,
        input_boundary=input_data,
        output_boundary=result_a.output,
    )

    # 4. Fragment B on fresh VM2 from anchor state
    try:
        interp_b = MalbolgeInterpreter()
        restored_machine = anchor_state.to_machine()
        result_b = interp_b.execute_from_snapshot(
            restored_machine,
            fragment_b,
            input_buffer=iter(input_data),  # remaining input
            max_steps=max_steps,
            capture_machine=True,
        )
    except (StepLimitExceededError, MalbolgeRuntimeError) as e:
        return CompositionResult(
            program_name=program_name,
            program_length=len(opcodes),
            split_at=split_at,
            full_output=full_output, full_steps=full_steps, full_halted=full_halted,
            fragment_a_output=result_a.output, fragment_a_steps=result_a.steps,
            anchor_state_hash=anchor.identity.state_hash,
            fragment_b_output="", fragment_b_steps=0, fragment_b_halted=False,
            composed_output="", composition_match=False,
            anchor_register_match=False, anchor_tape_match=False,
            error=f"Fragment B failed: {e}",
        )

    # 5. Compare
    composed_output = result_a.output + result_b.output
    composition_match = (composed_output == full_output)

    # Verify anchor state matches
    anchor_register_match = (
        anchor_state.a == result_a.machine.a
        and anchor_state.c == result_a.machine.c
        and anchor_state.d == result_a.machine.d
    )
    anchor_tape_match = (list(anchor_state.tape) == list(result_a.machine.tape))

    return CompositionResult(
        program_name=program_name,
        program_length=len(opcodes),
        split_at=split_at,
        full_output=full_output,
        full_steps=full_steps,
        full_halted=full_halted,
        fragment_a_output=result_a.output,
        fragment_a_steps=result_a.steps,
        anchor_state_hash=anchor.identity.state_hash,
        fragment_b_output=result_b.output,
        fragment_b_steps=result_b.steps,
        fragment_b_halted=result_b.machine.halted,
        composed_output=composed_output,
        composition_match=composition_match,
        anchor_register_match=anchor_register_match,
        anchor_tape_match=anchor_tape_match,
    )
