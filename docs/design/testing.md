# Testing: simulador, trazas y CI headless

Estrategia de testing de la consola y los juegos. La decisión está en el
[ADR 0006](../adr/0006-testing-strategy.md); el ticket es
[#13](https://github.com/skalanux/toxinator/issues/13). El checklist de hardware
vive en [`manual-checklist.md`](manual-checklist.md).

> **Estado**: decidido; implementación pendiente. El repo todavía no tiene
> código del runtime.

## Objetivos

- Testear input, gestos, física, scoring, i18n y game loop sin hardware real.
- Reproducir bugs con trazas grabadas y un simulador determinista.
- Correr lo importante en CI (Linux, sin GPU dedicada, sin Android).
- Dejar explícito qué se valida a mano y con qué hardware.
- Evitar tests flaky: reloj inyectable, seed y tolerancias.

**No objetivos**

- Tests visuales/snapshot del launcher como gate de CI.
- Performance benchmarking en CI.
- Playwright del controlador web en el primer corte.
- Emular hardware real (Android) a nivel driver.
- CI con GPU o dispositivos físicos.

## Pirámide y layout

| Capa | Qué cubre | Dónde | CI |
|---|---|---|---|
| Unit | Lógica pura: input mapping, gestos, scoring, i18n, config, matemática de física | `tests/unit/` | Cada PR |
| Integration | `InputHub` + game loop + Bullet + `ShowBase` headless + loader | `tests/integration/` | Cada PR, serial |
| E2E | Launcher, lanzar un juego, controlador web | `tests/e2e/` | Smoke en cada PR; resto manual |
| Manual | Android, teclado/mouse, GPU, performance, checklist | `docs/testing/manual-checklist.md` | Release |

```text
tests/
  unit/
    input/
    gestures/
    scoring/
    i18n/
    config/
    physics/
  integration/
    input_hub/
    game_loop/
    physics/
    launcher/
  e2e/
    smoke/
  fixtures/
    traces/
games/maldito-pino/tests/
  unit/
  integration/
```

Los tests unitarios **no importan Panda3D**. Los de integración usan un
`ShowBase` headless y se ejecutan en serie; los unitarios pueden correr en
paralelo.

Markers:

- `slow`: integración pesada; se puede mover a un job aparte si crece.
- `physics`: usa Bullet y tolerancias.
- `sim`: requiere el simulador.
- `hardware`: requiere Android o gamepad real; nunca en CI.
- `gpu`: requiere GPU o performance; nunca en CI.

## Simulador de mandos

`ControllerSimulator` es una `ControllerSource` más del `InputHub`; no es un
mando especial ni un bypass del hub. Emite `ControllerFrame`s a 60 Hz con
`source="sim"`. La implementación actual es `KeyboardMouseSource` (teclado/mouse,
slot 4 por defecto); presets y trazas siguen pendientes.

```python
class ControllerSource(Protocol):
    info: ControllerInfo
    def start(self) -> None: ...
    def poll(self, dt: float) -> Sequence[ControllerFrame]: ...
    def stop(self) -> None: ...
```

### Backends

- **Teclado/mouse** (implementado): flechas/WASD a stick, Enter/J a ×, Esc/K a
  ○, L/I a □/△, Tab a `options`, Q/E a L1/R1; el mouse llena `pointer` y
  sintetiza un touch mientras hay un botón apretado. El launcher desactiva WASD
  para no chocar con los atajos S/D/C.
- **Gamepad** (opcional): un gamepad real maneja el estado virtual para presets
  que necesitan motion/pointer. Los gamepads reales siguen siendo fuentes
  normales; este backend es para pruebas del simulador.

La lógica de mapeo (`SimulatorState`) es Python puro y se testea sin Panda3D;
el backend de teclado/mouse se conecta a los eventos de Panda3D en el runtime.

### Presets

Presets TOML por juego, con secciones `buttons`, `axes`, `motion` y `macros`.
Built-in: `default`, `bowling`, `kart`, `tennis`. Un juego puede shipear
`games/<id>/sim/<preset>.toml` y declararlo en el manifest:

```toml
[game]
sim_preset = "bowling"
```

```toml
# games/maldito-pino/sim/bowling.toml
name = "bowling"

[buttons]
space = "A"
b = "B"
enter = "Plus"

[axes]
left = "left_x"
right = "left_x"
up = "left_y"
down = "left_y"

[motion]
mouse_drag_x = "gyro.y"
mouse_drag_y = "gyro.x"

[macros.swing]
key = "s"
duration = 0.6
accel = [[0.0, 0.0, 9.81], [0.0, 0.0, 9.81]]
```

El schema exacto se cierra en la implementación; el diseño fija las secciones y
la resolución: preset del juego → preset built-in → `default`.

### CLI y overlay

```bash
toxinator --sim
toxinator dev --sim --sim-preset bowling --sim-slots 2
toxinator --sim --sim-gamepad --sim-noise 0.02
```

`F1` en dev muestra un overlay con preset, fuente, slot, botones, ejes,
accel/gyro, pointer y touch. El overlay no existe en release. El simulador
también sirve en el launcher para probar mandos, join/leave y estados de error.

## Trazas

Formato **JSONL** versionado. Una línea `meta`, líneas `frame` y líneas `event`.
UTF-8; `.jsonl.gz` opcional. `trace_version = 1`.

```jsonl
{"type":"meta","trace_version":1,"created_at":"2026-11-17T12:00:00Z","commit":"1b16b64","app_version":"0.1.0","game":"maldito-pino","locale":"es","platform":"linux-x86_64","controllers":[{"id":"sim-0","source":"sim","capabilities":["buttons","axes","motion","gyro","pointer","touch"]}],"sim_preset":"bowling","seed":1234,"duration":12.5}
{"type":"frame","t":0.0,"controller_id":"sim-0","buttons":["cross"],"axes":{"move_x":0.0,"move_y":0.0},"accel":[0.0,0.0,9.81],"gyro":[0.0,0.0,0.0],"orientation":[0.0,0.0,0.0,1.0],"pointer":[0.5,0.5],"touch":[]}
{"type":"event","t":0.0,"kind":"join","controller_id":"sim-0","slot":0}
```

- `t` es relativo al inicio, en segundos, no decreciente.
- `buttons` es una lista ordenada; `axes` un objeto; `accel`/`gyro` arrays de 3;
  `orientation` un cuaternión `[x,y,z,w]`; `pointer` `[x,y]`; `touch` una lista
  de puntos `{id,x,y,pressure}`.
- `event.kind`: `join`, `leave`, `assign`, `disconnect`, `calibration`.
- `meta` guarda commit, versión, juego, locale, plataforma, controllers, preset,
  seed y duración para reproducir.
- Se graba el `ControllerFrame` **normalizado**, no los sensores crudos. La
  calibración se testea con fixtures sintéticos de entrada cruda aparte; si hace
  falta depurar calibración, se agrega un formato raw después.

### Grabación

`InputHub.start_recording(path)` / `stop_recording()`; en CLI, `--record`.
Graba fuentes reales y simuladas con el mismo formato. Las trazas reales van a
`$XDG_DATA_HOME/toxinator/traces/` (o `~/.local/share/toxinator/traces`) y están
gitignoreadas; pueden contener coordenadas de touch, así que no se commitean.
Las trazas sintéticas van a `tests/fixtures/traces/`: `bowling_strike.jsonl`,
`kart_tilt.jsonl`, `tennis_swing.jsonl`.

### Replay

`ReplaySource` lee la traza y emite los frames según el tiempo de juego; no usa
sleeps ni wall clock. En tests se combina con `FakeClock`; en dev, `--replay`
puede correr en tiempo real o en loop. Preserva `t` para análisis de latencia y
permite `--replay-loop` y `--replay-speed`.

La validación de schema (`trace_version`, campos requeridos, `t` no decreciente,
controllers declarados, duración) corre en tests y en un comando de debug.

## Determinismo

- **Clock**: `Clock` inyectable en `GameContext` (`ctx.clock`). `RealClock` usa
  `time.monotonic()`; `FakeClock` avanza a mano en tests. La lógica de juego no
  llama `time.time()`.
- **Paso fijo**: física 1/120 con accumulator; render variable; clamp de `dt`
  máximo (0.25 s) para evitar spiral of death.
- **Pausa**: el game loop pone `dt = 0` y no avanza el tiempo de juego; el clock
  real sigue corriendo por debajo.
- **RNG**: `ctx.rng` es un `random.Random` seedeado. El seed viene de
  `TOXINATOR_SEED`, CLI o traza; se graba en `meta`. Nada de `random` global en
  lógica de juego.
- **Replay**: input determinista por frame/tiempo; sin wall clock en tests.
- **Física**: misma build/plataforma; tolerancia configurable por test (punto de
  partida: posición ±1 mm, velocidad ±1 cm/s, pinos caídos exactos; se ajusta en
  #16). Nunca igualdad exacta de floats.
- **Scoring/gestos**: tablas de casos y frames sintéticos; property-based queda
  para después, si aporta.

## CI y headless

Job de PR:

```bash
uv sync --frozen
uv run ruff check
uv run mypy
uv run pytest tests/unit games/maldito-pino/tests/unit
xvfb-run -a uv run pytest tests/integration -m "not hardware and not gpu" --maxfail=1
xvfb-run -a uv run pytest tests/e2e -m smoke
uv run python scripts/i18n.py check
```

- `ShowBase` headless con `windowType="none"`; si el pipe exige framebuffer,
  `windowType="offscreen"`. Audio null en CI.
- Un fixture de sesión crea el `ShowBase`; cada test resetea escena, tasks y
  servicios. Integración serial (sin `pytest-xdist`); unitarios pueden usar
  `-n auto`.
- Sin `/dev/input`, sin red real, sin GPU: `evdev`, WebSocket y mandos se testean
  con fakes o con el simulador.
- Presupuesto: unit < 2 min, integración < 5 min, smoke < 2 min. Si la
  integración crece, los `slow` pasan a un job aparte.

Cobertura: 80% en `toxinator.core`, `toxinator.input`, `toxinator.physics` y las
reglas de `maldito-pino`. UI, render y bootstrap quedan fuera del gate; el
reporte global se publica igual.

## Checklist manual

[`manual-checklist.md`](manual-checklist.md) cubre Android, teclado/mouse,
launcher, Maldito Pino, performance e i18n. Cada ítem registra pasos, esperado,
resultado, commit, fecha y hardware. El checklist es gate de release, no de PR.

## Riesgos y preguntas abiertas

- **GL headless**: `window-type none` puede no tener framebuffer; el fallback es
  `offscreen`. Si Mesa/llvmpipe falla en CI, se evalúa `p3tinydisplay`.
- **`ShowBase` singleton**: un fixture de sesión y reset por test; si aparece
  contaminación, los tests de integración se separan en procesos.
- **Tamaño de trazas**: JSONL es legible pero pesado; `.jsonl.gz` y muestreo se
  evalúan con sesiones largas.
- **Playwright del controlador web**: se agrega si el PWA crece; hoy es manual.
- **Hardware real**: Android disponible; el simulador de teclado/mouse cubre el
  desarrollo cotidiano. El checklist se completa cuando haya hardware.
