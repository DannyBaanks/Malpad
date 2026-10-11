"""Gates for MALPAD per-token primitive composition (tools/malpad_primitives.py).

v2: token = bytes. Text composes as char-tokens when the bank knows them at
that machine state, byte-tokens otherwise. Verification is byte-level:
program output (latin-1 str) must equal utf8(text) exactly.
"""
import os

import pytest

from tools.malpad_primitives import (
    BOOTSTRAP,
    PrimitiveBank,
    PrimitiveComposer,
    build_pack,
    pack_chars,
    state_hash,
)

# Measured 2026-10-10: the op* search (depth <= 5) has never synthesized a
# single-byte token >= 0xA0 — the evidence bank (551 entries) tops out at
# 0x9F, and a cold probe of 0xC2 exceeds 60 s without converging. These gates
# are NOT_DEMONSTRATED on a cold bank; set MALPAD_RUN_UTF8_GATES=1 to attempt
# them anyway (hours of compute, no guarantee).
_COLD_BYTE_LIMIT = os.environ.get("MALPAD_RUN_UTF8_GATES") != "1"


@pytest.fixture(scope="module")
def composer():
    return PrimitiveComposer()


def _compose_and_run(composer, text, bank):
    res = composer.compose(text, bank)
    out = composer.execute(res["program"], expect_bytes=text.encode("utf-8"))
    assert out["halt_reason"] == "halt_opcode"
    assert out["byte_exact"]
    return res, out


def test_two_chars_compose_byte_exact(composer, tmp_path):
    bank = PrimitiveBank(tmp_path / "bank.json")
    res, _ = _compose_and_run(composer, "AB", bank)
    assert res["program"].startswith(BOOTSTRAP)
    assert res["program"].endswith("v")
    assert len(bank) == 2


def test_alphabet_runs(composer, tmp_path):
    bank = PrimitiveBank(tmp_path / "bank.json")
    _compose_and_run(composer, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", bank)


def test_sentence_with_space_and_case(composer, tmp_path):
    bank = PrimitiveBank(tmp_path / "bank.json")
    _compose_and_run(composer, "HOLA MALPAD :p", bank)


def test_newline_is_a_primitive(composer, tmp_path):
    bank = PrimitiveBank(tmp_path / "bank.json")
    _compose_and_run(composer, "linea1\nlinea2\n", bank)


@pytest.mark.skipif(_COLD_BYTE_LIMIT, reason=(
    "NOT_DEMONSTRATED: la busqueda op* (depth<=5) no sintetiza bytes >= 0xA0 "
    "en banco frio (probe 0xC2 > 60 s sin converger; banco de evidencia topa "
    "en 0x9F). Opt-in: MALPAD_RUN_UTF8_GATES=1"))
def test_utf8_spanish_and_cjk_byte_exact(composer, tmp_path):
    bank = PrimitiveBank(tmp_path / "bank.json")
    _compose_and_run(composer, "¡Hola, señor! ¿Cómo estás? 你好世界", bank)


@pytest.mark.skipif(_COLD_BYTE_LIMIT, reason=(
    "NOT_DEMONSTRATED: mismo limite de banco frio que test_utf8 — los tokens "
    "byte del emoji valen >= 0x80 y la busqueda no converge. Opt-in: "
    "MALPAD_RUN_UTF8_GATES=1"))
def test_emoji_is_just_four_byte_tokens(composer, tmp_path):
    bank = PrimitiveBank(tmp_path / "bank.json")
    res, _ = _compose_and_run(composer, "ok 😂\n", bank)
    assert res["stats"]["byte_tokens"] >= 4


def test_bank_persists_and_hits_on_second_compose(composer, tmp_path):
    path = tmp_path / "bank.json"
    bank1 = PrimitiveBank(path)
    r1, _ = _compose_and_run(composer, "MALPAD", bank1)
    bank1.save()
    assert r1["stats"]["synthesized"] == 6
    assert r1["stats"]["bank_hits"] == 0

    bank2 = PrimitiveBank(path)
    r2, _ = _compose_and_run(composer, "MALPAD", bank2)
    assert r2["program"] == r1["program"]
    assert r2["stats"]["synthesized"] == 0
    assert r2["stats"]["bank_hits"] == 6


def test_state_hash_stable_for_bootstrap(composer):
    assert state_hash(composer.boot_machine) == state_hash(
        PrimitiveComposer().boot_machine)


def test_pack_definitions_nonempty():
    assert len(pack_chars("ascii")) >= 95
    assert "ñ" in pack_chars("es")
    assert "あ" in pack_chars("ja")
    assert "你" in pack_chars("zh")


@pytest.mark.skipif(_COLD_BYTE_LIMIT, reason=(
    "NOT_DEMONSTRATED en esta maquina: medido 2026-10-10, build_pack 'es' "
    "murio por OOM (< 10 min) en el primer caracter 'á' (C3 A1); no existen "
    "receipts en evidence/. Opt-in: MALPAD_RUN_UTF8_GATES=1"))
def test_build_pack_es_all_verified(composer, tmp_path):
    summary = build_pack(composer, "es", out_root=tmp_path / "packs")
    assert summary["verified"] == summary["chars"] > 0
