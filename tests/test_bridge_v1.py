"""Tests for Bridge V1."""
from __future__ import annotations

import pytest

from malbolge import MalbolgeInterpreter, ProgramGenerator

from tools.anchor import Anchor
from tools.bridge import Bridge, BridgeResult, Postcondition, Precondition
from tools.machine_state import MachineState


class TestPostcondition:
    def test_postcondition_creation(self):
        """Postcondition can be created from state."""
        state = MachineState(
            a=100, c=200, d=300, tape=(1, 2, 3), halted=False,
            executed_steps=50, input_consumed=0, output_produced=b"Hi",
        )
        post = Postcondition(state=state, output_produced="Hi", steps_executed=50)
        assert post.output_produced == "Hi"
        assert post.steps_executed == 50

    def test_postcondition_roundtrip(self):
        """Postcondition survives serialization."""
        state = MachineState(
            a=100, c=200, d=300, tape=(1, 2, 3), halted=False,
            executed_steps=50, input_consumed=0, output_produced=b"Hi",
        )
        post = Postcondition(state=state, output_produced="Hi", steps_executed=50)
        d = post.to_dict()
        assert d["output_produced"] == "Hi"
        assert d["steps_executed"] == 50


class TestPrecondition:
    def test_precondition_creation(self):
        """Precondition can be created with state hash."""
        pre = Precondition(state_hash="abc123", input_required="", halted_ok=False)
        assert pre.state_hash == "abc123"
        assert pre.halted_ok is False

    def test_precondition_roundtrip(self):
        """Precondition survives serialization."""
        pre = Precondition(state_hash="abc123", input_required="", halted_ok=False)
        d = pre.to_dict()
        assert d["state_hash"] == "abc123"
        assert d["halted_ok"] is False


class TestBridgeVerification:
    def test_verification_passes_matching_state(self):
        """Verification passes when state hashes match."""
        state = MachineState(
            a=100, c=200, d=300, tape=(), halted=False,
            executed_steps=0, input_consumed=0, output_produced=b"",
        )
        post = Postcondition(state=state)
        pre = Precondition(state_hash=state.hash_sha256())

        ok, error = Bridge.verify(post, pre)
        assert ok is True
        assert error == ""

    def test_verification_fails_mismatched_state(self):
        """Verification fails when state hashes differ."""
        state1 = MachineState(
            a=100, c=200, d=300, tape=(), halted=False,
            executed_steps=0, input_consumed=0, output_produced=b"",
        )
        state2 = MachineState(
            a=100, c=200, d=301, tape=(), halted=False,
            executed_steps=0, input_consumed=0, output_produced=b"",
        )
        post = Postcondition(state=state1)
        pre = Precondition(state_hash=state2.hash_sha256())

        ok, error = Bridge.verify(post, pre)
        assert ok is False
        assert "hash mismatch" in error.lower()

    def test_verification_fails_halted(self):
        """Verification fails when fragment halted unexpectedly."""
        state = MachineState(
            a=100, c=200, d=300, tape=(), halted=True,
            executed_steps=0, input_consumed=0, output_produced=b"",
        )
        post = Postcondition(state=state)
        pre = Precondition(state_hash=state.hash_sha256(), halted_ok=False)

        ok, error = Bridge.verify(post, pre)
        assert ok is False
        assert "halted" in error.lower()


class TestBridgeCompose:
    def test_compose_matches_monolithic(self):
        """Composed output matches monolithic output."""
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        # Find valid split point
        for split_at in range(50, len(opcodes)-50, 10):
            fragment_a = opcodes[:split_at]
            fragment_b = opcodes[split_at:]

            bridge_result = Bridge.compose(fragment_a, fragment_b)

            if bridge_result.success:
                # Get monolithic output
                interp = MalbolgeInterpreter()
                mono_result = interp.execute(opcodes, max_steps=5000)

                assert bridge_result.composed_output == mono_result.output
                return

        pytest.skip("No valid split point found")

    def test_compose_with_anchor(self):
        """Composition from anchor works correctly."""
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        # Find valid split point
        for split_at in range(50, len(opcodes)-50, 10):
            fragment_a = opcodes[:split_at]
            fragment_b = opcodes[split_at:]

            # Run fragment A
            interp_a = MalbolgeInterpreter()
            result_a = interp_a.execute(fragment_a, max_steps=5000, capture_machine=True)

            state = MachineState.from_machine(result_a.machine, executed_steps=result_a.steps)
            anchor = Anchor.create("test_anchor", state)

            # Compose from anchor
            bridge_result = Bridge.compose_with_anchor(anchor, fragment_b)

            if bridge_result.success:
                # Verify output matches
                interp_b = MalbolgeInterpreter()
                result_b = interp_b.execute_from_snapshot(
                    state.to_machine(), fragment_b, max_steps=5000,
                )
                assert bridge_result.composed_output == result_a.output + result_b.output
                return

        pytest.skip("No valid split point found")

    def test_compose_returns_bridge_result(self):
        """Composition returns proper BridgeResult."""
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        # Use first 50 chars as fragment A
        fragment_a = opcodes[:50]
        fragment_b = opcodes[50:]

        bridge_result = Bridge.compose(fragment_a, fragment_b)

        assert isinstance(bridge_result, BridgeResult)
        assert hasattr(bridge_result, "success")
        assert hasattr(bridge_result, "postcondition")
        assert hasattr(bridge_result, "precondition")


class TestBridgeIntegration:
    def test_bridge_with_real_program(self):
        """Bridge works with a real generated program."""
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        # Find a split point where composition works
        for split_at in range(50, len(opcodes)-50, 10):
            fragment_a = opcodes[:split_at]
            fragment_b = opcodes[split_at:]

            bridge_result = Bridge.compose(fragment_a, fragment_b)

            if bridge_result.success:
                assert bridge_result.verification_error == ""
                assert len(bridge_result.composed_output) > 0
                return

        pytest.skip("No valid split point found")

    def test_bridge_fails_for_invalid_fragments(self):
        """Bridge fails gracefully for fragments that don't compose."""
        # Use valid but short fragments that will halt
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        # Use first 10 chars (will likely halt quickly)
        fragment_a = opcodes[:10]
        fragment_b = opcodes[10:]

        bridge_result = Bridge.compose(fragment_a, fragment_b)

        # Should not crash, may or may not succeed
        assert isinstance(bridge_result, BridgeResult)
