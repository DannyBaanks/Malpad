"""Tests for Word Bank V1."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from malbolge import MalbolgeInterpreter, ProgramGenerator

from tools.machine_state import MachineState
from tools.word_bank import WordBank, WordEntry, WordProvenance


class TestWordProvenance:
    def test_provenance_creation(self):
        """Provenance can be created from generation info."""
        prov = WordProvenance(
            program_hash="abc123",
            generation_method="program_generator",
            generation_params={"target": "Hi"},
        )
        assert prov.program_hash == "abc123"
        assert prov.generation_method == "program_generator"
        assert prov.generation_params["target"] == "Hi"

    def test_provenance_roundtrip(self):
        """Provenance survives serialization."""
        prov = WordProvenance(
            program_hash="abc123",
            generation_method="program_generator",
            generation_params={"target": "Hi"},
        )
        d = prov.to_dict()
        prov2 = WordProvenance.from_dict(d)
        assert prov == prov2


class TestWordEntry:
    def test_entry_creation(self):
        """Entry can be created with program and metadata."""
        entry = WordEntry.create(
            program="test_program",
            generation_method="program_generator",
            output="Hello",
            executed_steps=100,
        )
        assert entry.program == "test_program"
        assert entry.output == "Hello"
        assert entry.executed_steps == 100
        assert entry.provenance.generation_method == "program_generator"

    def test_entry_provenance_hash(self):
        """Entry provenance hash matches program hash."""
        entry = WordEntry.create(
            program="test_program",
            generation_method="test",
        )
        import hashlib
        expected = hashlib.sha256("test_program".encode()).hexdigest()
        assert entry.provenance.program_hash == expected

    def test_entry_roundtrip(self):
        """Entry survives serialization."""
        entry = WordEntry.create(
            program="test_program",
            generation_method="test",
            output="Hello",
            executed_steps=50,
        )
        d = entry.to_dict()
        entry2 = WordEntry.from_dict(d)
        assert entry2.program == entry.program
        assert entry2.output == entry.output
        assert entry2.executed_steps == entry.executed_steps


class TestWordBank:
    def test_add_and_retrieve(self):
        """Entry can be added and retrieved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank = WordBank(Path(tmpdir))

            entry = WordEntry.create(
                program="test_program",
                generation_method="test",
                output="Hello",
            )
            entry_id = bank.add(entry)

            retrieved = bank.get(entry_id)
            assert retrieved is not None
            assert retrieved.program == "test_program"
            assert retrieved.output == "Hello"

    def test_find_by_output(self):
        """Entries can be found by output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank = WordBank(Path(tmpdir))

            entry1 = WordEntry.create(program="prog1", generation_method="test", output="Hi")
            entry2 = WordEntry.create(program="prog2", generation_method="test", output="Hello")
            entry3 = WordEntry.create(program="prog3", generation_method="test", output="Hi")

            bank.add(entry1)
            bank.add(entry2)
            bank.add(entry3)

            hi_entries = bank.find_by_output("Hi")
            assert len(hi_entries) == 2

    def test_find_by_method(self):
        """Entries can be found by generation method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank = WordBank(Path(tmpdir))

            entry1 = WordEntry.create(program="prog1", generation_method="generator", output="A")
            entry2 = WordEntry.create(program="prog2", generation_method="manual", output="B")

            bank.add(entry1)
            bank.add(entry2)

            gen_entries = bank.find_by_method("generator")
            assert len(gen_entries) == 1

    def test_verify_entry(self):
        """Entry verification validates program hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank = WordBank(Path(tmpdir))

            entry = WordEntry.create(
                program="test_program",
                generation_method="test",
                output="Hello",
            )
            entry_id = bank.add(entry)

            result = bank.verify_entry(entry_id)
            assert result["valid"] is True
            assert result["program_hash_ok"] is True

    def test_verify_nonexistent_entry(self):
        """Verifying nonexistent entry returns invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank = WordBank(Path(tmpdir))
            result = bank.verify_entry("nonexistent")
            assert result["valid"] is False

    def test_list_entries(self):
        """All entries can be listed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank = WordBank(Path(tmpdir))

            entry1 = WordEntry.create(program="prog1", generation_method="test", output="A")
            entry2 = WordEntry.create(program="prog2", generation_method="test", output="B")

            id1 = bank.add(entry1)
            id2 = bank.add(entry2)

            entries = bank.list_entries()
            assert len(entries) == 2
            assert id1 in entries
            assert id2 in entries


class TestWordBankIntegration:
    def test_store_program_with_state(self):
        """Program with captured state can be stored and retrieved."""
        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")

        interp = MalbolgeInterpreter()
        exec_result = interp.execute(result.opcodes, max_steps=5000, capture_machine=True)

        state = MachineState.from_machine(
            exec_result.machine,
            executed_steps=exec_result.steps,
            output_produced=exec_result.output.encode(),
        )

        entry = WordEntry.create(
            program=result.opcodes,
            generation_method="program_generator",
            generation_params={"target": "Hi"},
            output=exec_result.output,
            state=state,
            executed_steps=exec_result.steps,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            bank = WordBank(Path(tmpdir))
            entry_id = bank.add(entry)

            retrieved = bank.get(entry_id)
            assert retrieved is not None
            assert retrieved.output == "Hi"
            assert retrieved.state is not None
            assert retrieved.state.a == state.a

    def test_store_program_with_anchor(self):
        """Program with anchor can be stored and verified."""
        from tools.anchor import Anchor

        gen = ProgramGenerator()
        result = gen.generate_for_string("Hi")

        interp = MalbolgeInterpreter()
        exec_result = interp.execute(result.opcodes, max_steps=5000, capture_machine=True)

        state = MachineState.from_machine(
            exec_result.machine,
            executed_steps=exec_result.steps,
            output_produced=exec_result.output.encode(),
        )

        anchor = Anchor.create("test_anchor", state)

        entry = WordEntry.create(
            program=result.opcodes,
            generation_method="program_generator",
            output=exec_result.output,
            state=state,
            executed_steps=exec_result.steps,
        )
        entry.anchor = anchor

        with tempfile.TemporaryDirectory() as tmpdir:
            bank = WordBank(Path(tmpdir))
            entry_id = bank.add(entry)

            # Verify entry
            result = bank.verify_entry(entry_id)
            assert result["valid"] is True
            assert result["anchor_ok"] is True
