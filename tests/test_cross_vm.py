"""Cross-VM / Fresh Process tests.

Demonstrates that MachineState can survive a process boundary:
1. Serialize state to bytes
2. Spawn a new Python process
3. Deserialize state in the new process
4. Verify the state matches

This avoids false positives from Python object references staying alive.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from malbolge import MalbolgeInterpreter, ProgramGenerator

from tools.machine_state import MachineState

ROOT = Path(__file__).resolve().parent.parent


def _run_in_subprocess(code: str, input_data: bytes = b"") -> tuple[int, str, str]:
    """Run Python code in a subprocess and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        input=input_data,
        capture_output=True,
        timeout=30,
    )
    return result.returncode, result.stdout.decode("utf-8", errors="replace"), result.stderr.decode("utf-8", errors="replace")


class TestCrossVM:
    def test_state_survives_process_boundary(self):
        """MachineState survives serialization → new process → deserialization."""
        # Generate a program and run it
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        interp = MalbolgeInterpreter()
        exec_result = interp.execute(opcodes, max_steps=5000, capture_machine=True)

        state = MachineState.from_machine(
            exec_result.machine,
            executed_steps=exec_result.steps,
            output_produced=exec_result.output.encode(),
        )

        # Serialize to bytes
        state_bytes = state.to_bytes()

        # Verify in subprocess
        tape_sample = list(state.tape[:10])
        code = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
import tools.malpad_bootstrap; tools.malpad_bootstrap.apply()
from tools.machine_state import MachineState

# Deserialize
state_bytes = {state_bytes!r}
state = MachineState.from_bytes(state_bytes)

# Verify fields
assert state.a == {state.a}, f"a mismatch: {{state.a}}"
assert state.c == {state.c}, f"c mismatch: {{state.c}}"
assert state.d == {state.d}, f"d mismatch: {{state.d}}"
assert state.halted == {state.halted}, f"halted mismatch: {{state.halted}}"
assert len(state.tape) == {len(state.tape)}, f"tape length mismatch: {{len(state.tape)}}"
assert state.executed_steps == {state.executed_steps}, f"steps mismatch"
assert state.output_produced == {state.output_produced!r}, f"output mismatch"

# Verify tape cells (first 10)
expected_tape = {tape_sample!r}
for idx, (got, exp) in enumerate(zip(state.tape[:10], expected_tape)):
    assert got == exp, f"tape[{{idx}}] mismatch: {{got}} != {{exp}}"

print("PASS: State verified in subprocess")
"""

        exit_code, stdout, stderr = _run_in_subprocess(code)
        assert exit_code == 0, f"Subprocess failed: {stderr}"
        assert "PASS" in stdout

    def test_fresh_vm_composition_in_subprocess(self):
        """Fragment composition works across process boundaries."""
        # Generate a program
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        # Find a valid split point
        split_at = None
        for sa in range(50, len(opcodes)-50, 10):
            interp_a = MalbolgeInterpreter()
            try:
                result_a = interp_a.execute(opcodes[:sa], max_steps=5000, capture_machine=True)
                interp_b = MalbolgeInterpreter()
                result_b = interp_b.execute_from_snapshot(
                    result_a.machine,
                    opcodes[sa:],
                    max_steps=5000,
                )
                if result_a.output + result_b.output == "Hi":
                    split_at = sa
                    break
            except Exception:
                continue

        if split_at is None:
            pytest.skip("No valid split point found")

        # Get state after fragment A
        interp_a = MalbolgeInterpreter()
        result_a = interp_a.execute(opcodes[:split_at], max_steps=5000, capture_machine=True)
        state = MachineState.from_machine(result_a.machine, executed_steps=result_a.steps)

        # Verify composition in subprocess
        code = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
import tools.malpad_bootstrap; tools.malpad_bootstrap.apply()
from malbolge import MalbolgeInterpreter
from tools.machine_state import MachineState

# Deserialize state
state_bytes = {state.to_bytes()!r}
state = MachineState.from_bytes(state_bytes)

# Restore to fresh interpreter
interp = MalbolgeInterpreter()
machine = state.to_machine()

# Run fragment B
fragment_b = {opcodes[split_at:]!r}
result = interp.execute_from_snapshot(machine, fragment_b, max_steps=5000)

if result.output == "Hi":
    print("PASS: Fragment B produced correct output in subprocess")
else:
    print(f"FAIL: Got {{result.output!r}} instead of 'Hi'")
    sys.exit(1)
"""

        exit_code, stdout, stderr = _run_in_subprocess(code)
        assert exit_code == 0, f"Subprocess failed: {stderr}"
        assert "PASS" in stdout

    def test_state_file_roundtrip(self):
        """MachineState survives file serialization → new process → deserialization."""
        # Generate a program and run it
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")
        opcodes = result.opcodes

        interp = MalbolgeInterpreter()
        exec_result = interp.execute(opcodes, max_steps=5000, capture_machine=True)

        state = MachineState.from_machine(
            exec_result.machine,
            executed_steps=exec_result.steps,
            output_produced=exec_result.output.encode(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.bin"
            state_file.write_bytes(state.to_bytes())

            # Verify in subprocess
            code = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
import tools.malpad_bootstrap; tools.malpad_bootstrap.apply()
from tools.machine_state import MachineState

state = MachineState.from_bytes(open(r"{state_file}", "rb").read())

assert state.a == {state.a}
assert state.c == {state.c}
assert state.d == {state.d}
assert len(state.tape) == {len(state.tape)}
print("PASS: File roundtrip verified in subprocess")
"""

            exit_code, stdout, stderr = _run_in_subprocess(code)
            assert exit_code == 0, f"Subprocess failed: {stderr}"
            assert "PASS" in stdout
