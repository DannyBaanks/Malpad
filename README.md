# MALPAD

Editor de texto interactivo cuyas **semanticas de edicion se ejecutan en Malbolge clasico**. Los adaptadores del host solo transportan entrada/salida y materializan capacidades explicitamente autorizadas.

```
Malbolge decide QUE hacer.
El host solo transporta entrada/salida y, cuando aplica,
materializa capacidades del host explicitamente solicitadas.
```

**Si el adaptador tuvo que "entender" que edicion hacer, hicimos trampa.**

## Estado

| Milestone | Gate | Status | Evidence |
|-----------|------|--------|----------|
| M0 | contracts frozen | **DEMONSTRATED** | PROTOCOL/STATE_MODEL/HOST_BOUNDARY + 18 tests |
| M1 | echo loop | **DEMONSTRATED** | echo cross-backend (A/ABC/HELLO); quit-on-sentinel DEMONSTRATED 2026-10-11: `evidence/m1_quit_sentinel`, 5/5 vectores byte-exact en C reference + oracle_classic |
| M2 | input branching | **PARTIAL** | truth-machine cross-backend (0→halt, 1→loop); full editor state NOT_DEMONSTRATED (sin cursor_state no se promueve) |
| M3 | editable buffer | **PARTIAL** | seam de transporte: evidence/m3_buffer_authority + tools/buffer_adapter.py. End-to-end en Malbolge NOT_DEMONSTRATED; narrowed: dispatch N-way + store/load 2-slot + reverse AB→BA DEMOSTRADOS (2026-10-11); open: cursor_state, depth>2, shifting |
| M4 | logical render | **DEMONSTRATED** | terminal model from @MALPAD: events, presentation-only |
| M5 | ANSI adapter | **DEMONSTRATED** | model → ANSI, deterministic, backend-independent |
| M7 | save authority seam | **DEMOSTRADO** | request vs authority separated; write/deny/fail + receipts |
| Bridge | Python body ↔ Malbolge brain | **DEMONSTRATED** | generated Malbolge emits @MALPAD: frames, parsed → model → ANSI |
| Compiler | IR→Malbolge lowering | **PARTIAL** | 5/8 primitivas DEMONSTRATED (read, emit, halt-loop, mutable_cell_store, mutable_cell_load); cursor_state y buffer_mutate NOT_DEMONSTRATED con cotas |

Dashboard completo: `MALPAD_STATUS.md`.

## Infraestructura de Composicion

Sistema completo para componer programas Malbolge via fragmentos:

| Componente | Archivo | Descripcion |
|------------|---------|-------------|
| **MachineState** | `tools/machine_state.py` | Estado canonical inmutable (a, c, d, tape, halted). Serializacion binaria/JSON, SHA-256 |
| **Anchor** | `tools/anchor.py` | Punto de reset conocido para composicion. Identity + state + verificacion |
| **Composition** | `tools/composition.py` | Split → run A → capture → restore → run B → compare |
| **Word Bank** | `tools/word_bank.py` | Almacenamiento de programas con provenance criptografica |
| **Bridge** | `tools/bridge.py` | Postcondition → precondition verification y composicion |
| **Primitive Reevaluation** | `tools/primitive_reevaluation.py` | Reevaluacion de primitivas con infraestructura de composicion |

### Primitivas del Compilador

| Primitiva | Status | Clasificacion |
|-----------|--------|---------------|
| read_input | DEMONSTRATED | A (Composable) |
| emit_event | DEMONSTRATED | A (Composable) |
| halt_loop | DEMONSTRATED | A (Composable) |
| branch_simple | **DEMONSTRATED** | B (truth-machine + N-way dispatch) |
| compare_input | **DEMONSTRATED** | B (byte_dispatch18 21/21 + m1_quit_sentinel 6-way 5/5) |
| mutable_cell_load | **DEMONSTRATED** | B (A05b LIFO pop; AB→BA reverse 7/7) |
| mutable_cell_store | **DEMONSTRATED** | B (A05b LIFO slot cells) |
| cursor_state | NOT_DEMONSTRATED | C (cotas exhaustivas 2026-10-11, ver Limites Negativos) |
| buffer_mutate | NOT_DEMONSTRATED | D (cadena de dependencias en `evidence/buffer_mutate/GATES.md`) |

### Limites Negativos

**Preexistentes (GENEALOGIA_MALBOLGE):**
- **P2'**: 37,376 candidatos (len 3-5), 0 hits → dispatch imposible en programas cortos
- **P4'**: 2.1M candidatos (len 7), 3884 con 3 outputs pero 0 con loop
- **long_search**: 0 programas len 7 corriendo ≥50 steps
- **Conclusion**: cursor_state requiere programas ≥170 chars con self-modifying code + arithmetic

**Nuevas cotas 2026-10-11 (`evidence/cursor_state_search`):**
- **Censo straight-delta** desde snapshot truth-machine, alfabeto `op*` ≤13: **0/2,391,483** candidatos (EXHAUSTIVE, 206 s)
- **Censo extendido** `op*/i` ≤9: **0/12,093,234** candidatos (EXHAUSTIVE, 348 s)
- **Sonda MBIR** (ruta por VM ALU): NEGATIVA — ADD→ADD/SUB→SUB y post-OUT producen basura ("result never lands in Slot 0", defecto upstream abierto en MB-DATABASE); probe canonica `mbir_alu_cursor_probe.json`
- **Busqueda de corpus buffer_mutate** (GENEALOGIA/MB-DATABASE/MALBOLGE/MalbolgeFree): negativa — ningun espécimen shift/depth>2

## Contrato del nucleo (congelado)

- **Input**: 1 byte = 1 token. ASCII imprimible inserta; bytes de control son
  teclas normalizadas (BACKSPACE 0x08, ENTER 0x0A, LEFT/RIGHT/UP/DOWN 0x11–0x14,
  SAVE 0x17, QUIT 0x04, save ACK/DENIED/ERROR 0x41/0x44/0x45).
- **Output**: tramas `@MALPAD:<EVENT>[:<arg>]` por linea.
- **Estado**: BOOT → READY ⇄ WAIT_SAVE_ACK → HALTED. Buffer fijo 80 ASCII,
  una linea (v0), cursor 0..buffer_len.
- **Limite del host**: adaptador transporta/renderiza/materializa; nunca decide
  un caracter, movimiento de cursor, borrado, o intencion de save/quit.

Docs: `docs/PROTOCOL.md`, `docs/STATE_MODEL.md`, `docs/HOST_BOUNDARY.md`.

## Referencia ejecutable

`tools/editor_ir.py` es el **oraculo de contrato en tiempo de construccion** — implementa
el modelo de estado congelado textualmente para que el contrato sea ejecutable y testeable.
NO es la logica del editor final: M2+ requiere un especimen de Malbolge cuyo comportamiento
ejecutado coincida con este IR, verificado en interpretes independientes.

## Pruebas

```bash
python3 -m pytest tests -q     # 123–124 pasadas, 19–20 skipped (Linux, 2026-10-11;
                               # test_bridge_v1 añade 0–1 skip flaky por split-point aleatorio)
```

**Limite medido**: la busqueda `op*` (depth<=5) jamas sintetizo un token byte
`>=0xA0` desde estado frio (banco de evidencia topa en 0x9F; STRAZ registro
TIMEOUT en `a5`; probes 2026-10-10). Las gates UTF-8 de
`test_malpad_primitives.py` se saltan con razon `NOT_DEMONSTRATED`;
opt-in con `MALPAD_RUN_UTF8_GATES=1` (horas de compute, sin garantia).
Requiere ademas el paquete `malbolge` del toolkit (`MALBOLGE_TOOLKIT_DIR`).

### Suite de pruebas

| Test | Tests | Descripcion |
|------|-------|-------------|
| test_compiler.py | 9 | Compilador IR→Malbolge (status honesto) |
| test_bridge.py | 4 | Bridge Python↔Malbolge |
| test_m1_echo.py | 5 | Echo loop (M1) |
| test_m1_sentinel.py | 3 | M1 quit-on-sentinel: ejemplar Classic con sha256 fijado, 5 vectores byte-exact en C reference + oracle_classic |
| test_m2_state.py | 4 | State/branching (M2) |
| test_m3_buffer.py | 4 | Buffer authority seam (M3) |
| test_malpad_primitives.py | 10 | Composicion por tokens con banco persistente (3 gates UTF-8 opt-in) |
| test_m45_render.py | 6 | Render + ANSI (M4/M5) |
| test_m7_save.py | 6 | Save authority seam (M7) |
| test_mutable_cell.py | 2 | Mutable cell cross-backend |
| test_mutable_cell_reverse.py | 3 | AB→BA puro: espécimen LIFO A05b (sha256 fijado), 5 vectores en oracle_classic + C reference |
| test_fragment_epoch_transparency.py | 17 | Fragment composition transparency |
| test_cross_vm.py | 3 | Cross-VM state survival |
| test_negative_controls.py | 7 | Negative controls |
| test_word_bank.py | 13 | Word Bank V1 |
| test_bridge_v1.py | 9 | Bridge V1 composition |
| test_cursor_state.py | 5 | Cursor state composition |
| test_primitive_reevaluation.py | 10 | Primitive reevaluation |

Fixtures: `tests/fixtures/keystrokes/*.keys.bin` → `tests/fixtures/expected/*.events.txt`.
El vector de demo congelado `demo` escribe `HELLO ← ← ⌫ A ↵ MALBOLGE`, luego
`SAVE ACK QUIT`, y tiene que terminar siempre en buffer `HEAMALBOLGELO`, cursor 11.

Guia del operador humano: `GUIA.md`.

## Evidencia

```
evidence/
├── FRAGMENT_COMPOSITION_V1/    # Composition infrastructure
│   ├── README.md               # Summary
│   ├── RESULTS.md              # Detailed results
│   └── machine_state_schema.json
├── m0/                         # M0 contracts evidence
├── m1_echo/                    # M1 echo loop evidence
├── m1_quit_sentinel/           # M1 quit-on-sentinel specimen (5/5, sha256 fijado)
├── m2_state/                   # M2 state/branching evidence
├── m3_buffer/                  # M3 gate GATES.md (+ Correction 2026-10-11)
├── m3_buffer_authority/        # M3 buffer authority seam (transporte host)
├── m45_render/                 # M4/M5 render evidence
├── m7_save/                    # M7 save authority evidence
├── mutable_cell/               # mutable cell cross-backend
├── mutable_cell_reverse/       # AB→BA puro (A05b LIFO, 7/7, sha256 fijado)
├── cursor_state_search/        # censos exhaustivos + sonda MBIR (negativos)
├── buffer_mutate/              # cadena de dependencias gate (2026-10-11)
├── compiler/                   # compiler scaffolding evidence
├── malbolge_straz/             # Malbolge specimens (STRAZ)
├── malpad_primitives/          # token composition bank
└── m_bridge/                   # bridge oracle evidence
```

## Restricciones duras (de ROADMAP_MALPAD.md)

- Malbolge es dueño del estado del editor, mutaciones del buffer, semanticas del cursor,
  semanticas de comandos, decisiones de render, intencion de save, intencion de quit.
- Sin logica oculta del host. Sin syscalls fake. `capability != authority`.
- Mismo `.mal` + mismo script de keystrokes → mismo estado logico final en
  VMs clasicas de Malbolge independientes y (despues) en frontends ANSI + Win32.
- Sin claim de novedad historica aun.
