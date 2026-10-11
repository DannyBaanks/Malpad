"""
Test bootstrap: make the ecosystem importable without host-specific paths.

Two things the suite needs on `sys.path` and cannot assume:

1. The repo itself (`tools.` package imports) and `tools/` (bare-module imports
   like `from oracle import ...` / `from malbolge_compiler import ...`).
2. The `malbolge` package (MalbolgeInterpreter, ProgramGenerator) — it lives in
   the Malbolge toolkit checkout, a sibling project, not in this repo.

Resolution order for the toolkit, first hit wins:
  - $MALBOLGE_TOOLKIT_DIR (explicit, any layout)
  - <repo>/../ISyCo/workspace/malbolge_toolkit (this machine's layout)
  - <repo>/../../workspace/malbolge_toolkit (toolkit vendored inside a monorepo)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tools.malpad_bootstrap import apply as _apply  # noqa: E402

toolkit = _apply()
if toolkit is None:
    # Fail with a message instead of a bare ModuleNotFoundError from every test.
    collect_ignore = ["tests/test_bridge_v1.py", "tests/test_cross_vm.py",
                      "tests/test_cursor_state.py", "tests/test_fragment_epoch_transparency.py",
                      "tests/test_malpad_primitives.py", "tests/test_negative_controls.py",
                      "tests/test_word_bank.py", "tests/test_primitive_reevaluation.py"]
    sys.stderr.write(
        "MALPAD conftest: el paquete `malbolge` no se encontro. Exporta "
        "MALBOLGE_TOOLKIT_DIR apuntando al checkout del toolkit (el dir que "
        "contiene malbolge/__init__.py) para correr la suite completa.\n"
    )
