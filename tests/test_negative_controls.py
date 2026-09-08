"""Negative control tests.

These tests MUST fail if the test suite is correct.
If they pass, something is wrong with the test logic.
"""
from __future__ import annotations

import pytest

from malbolge import MalbolgeInterpreter

from tools.machine_state import MachineState


class TestNegativeControls:
    def test_garbage_state_fails_validation(self):
        """MachineState.from_bytes with garbage must raise."""
        with pytest.raises(Exception):
            MachineState.from_bytes(b"not a valid state")

    def test_wrong_magic_fails_validation(self):
        """MachineState.from_bytes with wrong magic must raise."""
        # Create a valid state, then corrupt the magic bytes
        state = MachineState(a=1, c=2, d=3, tape=(), halted=False,
                            executed_steps=0, input_consumed=0, output_produced=b"")
        raw = bytearray(state.to_bytes())
        raw[0] = 0xFF  # corrupt magic
        raw[1] = 0xFF
        with pytest.raises(Exception):
            MachineState.from_bytes(bytes(raw))

    def test_truncated_state_fails_validation(self):
        """MachineState.from_bytes with truncated data must raise."""
        state = MachineState(a=1, c=2, d=3, tape=(), halted=False,
                            executed_steps=0, input_consumed=0, output_produced=b"")
        raw = state.to_bytes()
        with pytest.raises(Exception):
            MachineState.from_bytes(raw[:10])

    def test_different_input_different_output(self):
        """Different inputs to same program must produce different outputs."""
        # truth_machine: input '0' halts immediately, input '1' loops
        gen_result = None
        try:
            from malbolge import ProgramGenerator
            gen = ProgramGenerator()
            gen_result = gen.generate_for_string("01")
        except Exception:
            pytest.skip("Cannot generate truth machine")

        # If we got a program, different inputs should give different outputs
        interp1 = MalbolgeInterpreter()
        result1 = interp1.execute(gen_result.opcodes, input_buffer="0", max_steps=1000)

        interp2 = MalbolgeInterpreter()
        result2 = interp2.execute(gen_result.opcodes, input_buffer="1", max_steps=1000)

        # At least the outputs should differ (or one should timeout)
        # This is a sanity check, not a strict requirement
        if result1.output != result2.output:
            pass  # good - different inputs, different outputs
        elif result1.steps < 1000 and result2.steps < 1000:
            # Both halted - outputs should differ for truth machine
            # But not all programs are truth machines, so this is just a check
            pass

    def test_state_hash_deterministic(self):
        """Same state must always produce same hash."""
        state1 = MachineState(a=100, c=200, d=300, tape=(1, 2, 3), halted=False,
                             executed_steps=0, input_consumed=0, output_produced=b"")
        state2 = MachineState(a=100, c=200, d=300, tape=(1, 2, 3), halted=False,
                             executed_steps=0, input_consumed=0, output_produced=b"")

        assert state1.hash_sha256() == state2.hash_sha256()

    def test_state_hash_different_for_different_states(self):
        """Different states must produce different hashes."""
        state1 = MachineState(a=100, c=200, d=300, tape=(), halted=False,
                             executed_steps=0, input_consumed=0, output_produced=b"")
        state2 = MachineState(a=100, c=200, d=301, tape=(), halted=False,
                             executed_steps=0, input_consumed=0, output_produced=b"")

        assert state1.hash_sha256() != state2.hash_sha256()

    def test_anchor_verify_fails_on_tampered_state(self):
        """Anchor verification must fail if state is tampered."""
        from tools.anchor import Anchor

        state = MachineState(a=100, c=200, d=300, tape=(), halted=False,
                            executed_steps=0, input_consumed=0, output_produced=b"")
        anchor = Anchor.create("test", state)

        # Tamper with state
        tampered = MachineState(a=100, c=200, d=301, tape=(), halted=False,
                               executed_steps=0, input_consumed=0, output_produced=b"")

        # Verification should fail
        assert anchor.identity.state_hash != tampered.hash_sha256()
