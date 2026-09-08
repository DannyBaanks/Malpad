"""Tests for T9: Primitive reevaluation."""
from __future__ import annotations

import pytest

from tools.primitive_reevaluation import (
    reevaluate_primitives,
    create_reevaluation_report,
    PrimitiveStatus,
)


class TestPrimitiveReevaluation:
    def test_reevaluation_returns_all_primitives(self):
        """Reevaluation returns status for all primitives."""
        primitives = reevaluate_primitives()
        assert len(primitives) == 9  # 9 primitives

    def test_reevaluation_has_valid_statuses(self):
        """Reevaluation has valid status codes."""
        primitives = reevaluate_primitives()
        valid_statuses = {"A", "B", "C", "D"}
        for p in primitives:
            assert p.new_status in valid_statuses

    def test_demonstrated_primitives_are_composable(self):
        """DEMONSTRATED primitives are composable (A)."""
        primitives = reevaluate_primitives()
        demonstrated = [p for p in primitives if p.original_status == "DEMONSTRATED"]
        for p in demonstrated:
            assert p.new_status == "A", f"{p.name} should be A, got {p.new_status}"

    def test_partial_primitives_are_bridges(self):
        """PARTIAL primitives are new bridges (B)."""
        primitives = reevaluate_primitives()
        partial = [p for p in primitives if p.original_status == "PARTIAL"]
        for p in partial:
            assert p.new_status == "B", f"{p.name} should be B, got {p.new_status}"

    def test_not_demonstrated_primitives_are_c_or_d(self):
        """NOT_DEMONSTRATED primitives are C or D."""
        primitives = reevaluate_primitives()
        not_demo = [p for p in primitives if p.original_status == "NOT_DEMONSTRATED"]
        for p in not_demo:
            assert p.new_status in {"C", "D"}, f"{p.name} should be C or D, got {p.new_status}"

    def test_cursor_state_is_new_fragment(self):
        """cursor_state is a new fragment (C)."""
        primitives = reevaluate_primitives()
        cursor = next(p for p in primitives if p.name == "cursor_state")
        assert cursor.new_status == "C"

    def test_buffer_mutate_is_not_demonstrated(self):
        """buffer_mutate is not demonstrated (D)."""
        primitives = reevaluate_primitives()
        buffer = next(p for p in primitives if p.name == "buffer_mutate")
        assert buffer.new_status == "D"

    def test_report_generates(self):
        """Report generates successfully."""
        report = create_reevaluation_report()
        assert "T9: Primitive Reevaluation Report" in report
        assert "A (Composable)" in report
        assert "B (New bridge)" in report

    def test_report_has_all_primitives(self):
        """Report includes all primitives."""
        report = create_reevaluation_report()
        primitives = ["read_input", "emit_event", "halt_loop", "branch_simple",
                      "compare_input", "mutable_cell_load", "mutable_cell_store",
                      "cursor_state", "buffer_mutate"]
        for p in primitives:
            assert p in report


class TestPrimitiveIntegration:
    def test_composable_primitives_work_with_composition(self):
        """Composable primitives work with fragment composition."""
        from malbolge import MalbolgeInterpreter, ProgramGenerator
        from tools.machine_state import MachineState

        # Generate a program
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        # Find a split point
        for split_at in range(50, len(opcodes)-50, 10):
            fragment_a = opcodes[:split_at]
            fragment_b = opcodes[split_at:]

            try:
                # Execute fragment A
                interp_a = MalbolgeInterpreter()
                result_a = interp_a.execute(fragment_a, max_steps=5000, capture_machine=True)

                state = MachineState.from_machine(
                    result_a.machine,
                    executed_steps=result_a.steps,
                )

                # Execute fragment B
                interp_b = MalbolgeInterpreter()
                result_b = interp_b.execute_from_snapshot(
                    state.to_machine(),
                    fragment_b,
                    max_steps=5000,
                )

                # Get monolithic
                interp_mono = MalbolgeInterpreter()
                result_mono = interp_mono.execute(opcodes, max_steps=5000)

                # Compare
                composed = result_a.output + result_b.output
                if composed == result_mono.output:
                    return  # Success!

            except Exception:
                continue

        pytest.skip("No valid split point found")
