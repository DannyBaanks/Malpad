"""MALPAD oracle — real Malbolge interpreter wrapper.

Replaces the old stub that returned pre-canned results for known programs.
Now uses the actual MalbolgeInterpreter from the malbolge package.

Status: Phase 1 — real oracle for cross-backend validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from malbolge import (
    MalbolgeInterpreter,
    normalize,
    MalbolgeRuntimeError,
    StepLimitExceededError,
)


class _OutputCapturingInterpreter(MalbolgeInterpreter):
    """Records emitted chars so a step-limit raise doesn't lose partial output.

    ``<`` is the only emitting opcode and the loop samples ``machine.a`` for
    it via ``_instruction_at`` before dispatch — hooking there captures
    exactly what the aborted run would have printed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.captured: list[str] = []

    def _instruction_at(self, index: int) -> str:
        instruction = super()._instruction_at(index)
        if instruction == "<":
            self.captured.append(chr(self.machine.a % 256))
        return instruction


@dataclass
class OracleResult:
    """Result from oracle execution. Compatible with existing test assertions."""
    output: str
    steps: int
    halted: bool
    halt_reason: str = ""
    status: str = "OK"


class Oracle:
    """Real Malbolge interpreter oracle.

    API matches the old stub:
        oracle.load_ascii(source_string)
        oracle.provide_input(input_string)
        result = oracle.run(max_steps=5000)

    Internally normalizes ASCII source to opcodes and executes via
    MalbolgeInterpreter.
    """

    def __init__(self):
        self._prog: str = ""
        self._inp: str = ""

    def load_ascii(self, p: str) -> Oracle:
        """Load Malbolge source code (ASCII representation)."""
        self._prog = p.strip()
        return self

    def provide_input(self, i: str) -> Oracle:
        """Provide input string for execution."""
        self._inp = i
        return self

    def run(self, max_steps: int = 5000) -> OracleResult:
        """Execute the loaded program with provided input.

        Returns OracleResult with output, steps, halted, halt_reason.
        Handles step limit exceeded (loop) and runtime errors gracefully.
        """
        interp = _OutputCapturingInterpreter()
        try:
            opcodes = normalize(self._prog)
            if len(opcodes) == 0:
                return OracleResult(
                    output="",
                    steps=0,
                    halted=True,
                    halt_reason="empty_program",
                    status="ERROR",
                )

            result = interp.execute(
                opcodes,
                input_buffer=iter(self._inp),
                max_steps=max_steps,
            )
            return OracleResult(
                output=result.output,
                steps=result.steps,
                halted=result.halted,
                halt_reason=result.halt_reason,
                status="OK",
            )

        except StepLimitExceededError:
            # Program looped beyond step limit — this is expected for
            # truth-machine input '1' and similar looping programs.
            # The interpreter aborts without returning its output buffer;
            # report what actually ran before the limit.
            return OracleResult(
                output="".join(interp.captured),
                steps=max_steps,
                halted=False,
                halt_reason="timeout",
                status="OK",
            )

        except MalbolgeRuntimeError as e:
            # Program crashed (invalid opcode, etc.)
            return OracleResult(
                output="",
                steps=0,
                halted=True,
                halt_reason=f"runtime_error: {e}",
                status="ERROR",
            )

        except Exception as e:
            # Unexpected error
            return OracleResult(
                output="",
                steps=0,
                halted=True,
                halt_reason=f"unexpected_error: {type(e).__name__}: {e}",
                status="ERROR",
            )


# Legacy constant for backward compatibility (used in tests)
CAT = '(=BA#9"=<;:3y7x54-21q/p-,+*)"!h%B0/.~P<<:(8&66#"!~}|{zyxwvugJ%'
