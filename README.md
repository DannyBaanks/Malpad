# MALPAD

Editor de texto interactivo cuyas **semanticas de edicion se ejecutan en Malbolge clasico**. Los adaptadores del host solo transportan entrada/salida y materializan capacidades explicitamente autorizadas.

```
Malbolge decide QUE hacer.
El host solo transporta entrada/salida y, cuando aplica,
materializa capacidades del host explicitamente solicitadas.
```

**Si el adaptador tuvo que "entender" que edicion hacer, hicimos trampa.**

## Estado

- **M0** (contratos congelados): `PROTOCOL_FROZEN`, `STATE_MODEL_FROZEN`,
  `HOST_BOUNDARY_EXPLICIT`.
- **M1** (echo loop): **PARCIAL**. Echo loop demostrado en 2 backends
  independientes (Malbolge-Engine C + malbolge-oracle): A→A, ABC→ABC, HELLO→HELLO.
  Input vacio → halt limpio en el engine. **Quit-on-specific-sentinel es
  NOT_DEMONSTRATED** (el programa para en EOF, no en un byte especifico — el
  caso dificil de input-branching es M2/M3). Ver `evidence/m1_echo/GATES.md`.
- **M2** (estado/cursor): **PARCIAL**. La **primitiva de input-branching esta
  DEMOSTRADA** via una truth-machine de Malbolge en 2 backends independientes (input
  `'0'` → halt, `'1'` → loop, identico en engine + oraculo). La **maquina de
  estados completa del editor (cursor+buffer+6-way dispatch) es NOT_DEMONSTRATED** — necesita
  un compilador IR→Malbolge para programas con input-branching con estado. Target congelado:
  `tests/editor_state_vectors.json`. Ver `evidence/m2_state/GATES.md`.
- **M3** (buffer editable de una linea): **NOT_DEMONSTRATED**. El muro es real
  y se reporta honestamente: no existe ningun programa Malbolge con input-branching
  y estado del que pueda one, ningun generador/compilador produce maquinas de estados
  con estado mutable (el `malbolge-generator` solo emite programas de salida de texto),
  y escribirlo a mano esta fuera del alcance practico. Cerrar M3 requiere construir el
  **compilador IR→Malbolge** (sub-proyecto multi-sesion, roadmap §8/§9). Ver
  `evidence/m3_buffer/GATES.md`.
- **M4** (render logico): **DEMOSTRADO**. El modelo de terminal consume eventos
  `@MALPAD:` de un limite neutro; solo presentacion (los CHAR edit ops nunca mutan
  el modelo). `evidence/m45_render/GATES.md`.
- **M5** (adaptador ANSI): **DEMOSTRADO**. modelo → ANSI, deterministico,
  backend-independiente (oraculo/fixture/espécimen indistinguibles).
- **M7** (costura de autoridad de guardado): **DEMOSTRADO**. El nucleo emite solo save REQUEST;
  el adaptador del host es dueño de la autoridad de escritura (politica → write/deny/error),
  recibos honestos. `SAVE capability != SAVE authority`. `evidence/m7_save/GATES.md`.

Dashboard honesto completo: `MALPAD_STATUS.md`.

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
py -m pytest tests -q          # 18 pruebas
```

Fixtures: `tests/fixtures/keystrokes/*.keys.bin` → `tests/fixtures/expected/*.events.txt`.
El vector de demo congelado `demo` escribe `HELLO ← ← ⌫ A ↵ MALBOLGE`, luego
`SAVE ACK QUIT`, y tiene que terminar siempre en buffer `HEAMALBOLGELO`, cursor 11.

Guia del operador humano: `GUIA.md`.

## Restricciones duras (de ROADMAP_MALPAD.md)

- Malbolge es dueño del estado del editor, mutaciones del buffer, semanticas del cursor,
  semanticas de comandos, decisiones de render, intencion de save, intencion de quit.
- Sin logica oculta del host. Sin syscalls fake. `capability != authority`.
- Mismo `.mal` + mismo script de keystrokes → mismo estado logico final en
  VMs clasicas de Malbolge independientes y (despues) en frontends ANSI + Win32.
- Sin claim de novedad historica aun.
