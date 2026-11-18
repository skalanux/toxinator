---
name: toxinator-game-dev
description: >-
  Build, extend, debug, test, and integrate games for the Toxinator console
  (Panda3D + Python). Use whenever the user creates or modifies a game, adds a
  game package in the external games directory or under games/, implements or
  changes the Game/GameContext/GameHost contract, manifest.toml, modes, HUD,
  scoring, physics, phone controls (A/B/touch/orientation), launcher catalog
  entries, or toxinator play integration; also use for Spanish requests like
  "crear un juego para Toxinator", "agregar un juego", "cómo construyo un
  juego" or "modificar Maldito Pino". Read this before guessing platform APIs
  or inventing services.
compatibility: >-
  Requires the toxinator repo (uv workspace), Python >=3.14,<3.15, Panda3D
  1.10.16, and uv. External games live outside the repo and use the console's
  venv. Some commands need a display or use --offscreen.
---

# Construir juegos para Toxinator

> **Estado del contrato**: API `0.1` (match exacto). Hay dos caminos: juegos
> **externos** en `~/Projects/toxinator-games` (recomendado) y juegos
> **built-in** en `games/` del repo (solo para el ejemplo/cartelera de la
> plataforma). Los externos aparecen en la **CARTELERA** del launcher al
> iniciar y se lanzan con A/ENTER; también con `toxinator play <id>`.
> i18n, audio, assets, settings, save, clock, rng y PhysicsWorld **no** están
> expuestos en `GameContext` aunque estén decididos en ADRs.
> Última revisión: 2026-11-18.

Toxinator es una consola 3D personal. La consola es dueña de un único `ShowBase`,
la ventana, el input, la red y el launcher. Un juego es un **plugin in-process**
que implementa reglas, contenido y presentación; no es una app independiente.

La regla que más rompe cosas si se ignora: un juego solo puede importar
`toxinator.api` del runtime. No importes `toxinator.core`, `.dev`, `.launcher`,
`.input` ni `.physics`; la frontera está en el
[ADR 0003](../../../docs/adr/0003-repo-layout-and-api-boundary.md).

## Dos formas de juego

| Camino | Dónde vive | Cómo se carga | Cuándo usarlo |
|---|---|---|---|
| **Externo** | `~/Projects/toxinator-games/<juego>/` | escaneo de `src/*/manifest.toml`, `create_game(manifest)` y CARTELERA del launcher | juegos nuevos, prototipos, repos separados |
| **Built-in** | `games/<juego>/` del repo | catálogo hardcodeado en `core/games.py` | ejemplo/cartelera oficial, tests de plataforma |

Para juegos nuevos, usá el camino externo. Mantené el repo de la plataforma
limpio de contenido de juego. Maldito Pino queda como referencia built-in.

## Flujo externo (recomendado)

1. Copiá el template:
   ```bash
   cd ~/Projects/toxinator-games
   cp -r _template mi-juego
   mv mi-juego/src/template_game mi-juego/src/mi_juego
   ```
2. Editá `src/mi_juego/manifest.toml` (`id`, `name`, etc.) y el paquete.
3. Implementá `src/mi_juego/game.py` y `create_game()` en `__init__.py`.
4. Ejecutá:
   ```bash
   cd /home/ska/Projects/toxinator
   uv run toxinator play mi-juego
   uv run toxinator play mi-juego --demo
   ```
5. Para verlo en la LIGA, reiniciá el launcher:
   ```bash
   uv run toxinator
   ```
   El juego aparece en la CARTELERA y se lanza con A/ENTER.

El directorio por defecto es `~/Projects/toxinator-games`. Para otra ruta:

```bash
export TOXINATOR_GAMES_DIR=/ruta/a/mis-juegos
```

El cargador agrega `src/` del juego al `sys.path`, importa el paquete y llama
`create_game(manifest)`. No instala paquetes ni crea un venv. Si el juego
necesita una dependencia extra, instalala en el venv de la consola.

## Contrato mínimo

```python
from toxinator.api import GameContext, GameManifest


class MiJuego:
    def __init__(self, manifest: GameManifest) -> None:
        self.manifest = manifest
        self.ctx: GameContext | None = None
        self.root = None
        self.ui_root = None

    def start(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self.root = ctx.scene.attach_new_node("mi-juego")
        self.ui_root = ctx.ui.attach_new_node("mi-juego-ui")
        # Escena, luces, cámara y HUD.

    def update(self, dt: float) -> None:
        if self.ctx is None:
            return
        state = self.ctx.input_state
        frame = state.frame(0)
        if frame is None:
            return
        # frame.button("A"), frame.touch, frame.orientation, etc.

    def stop(self) -> None:
        if self.ui_root is not None:
            self.ui_root.remove_node()
            self.ui_root = None
        if self.root is not None:
            self.root.remove_node()
            self.root = None
        self.ctx = None
```

El paquete externo necesita:

```python
# src/mi_juego/__init__.py
from toxinator.api import Game, GameManifest

from .game import MiJuego


def create_game(manifest: GameManifest) -> Game:
    return MiJuego(manifest)
```

Reglas:

- No crees `ShowBase`, ventanas ni `run()` propios.
- No leas input directo de Panda3D ni abras red. Usá `ctx.input_state`.
- No bloquees el hilo principal (`sleep`, `input()`, loops infinitos).
- `GameHost` limita `dt` a `0.0..0.1`; para física usá paso fijo y acumulador
  (Maldito Pino usa `DT = 1/120`).
- Limpiá nodos y recursos en `stop`. El host borra las raíces, pero no tus
  mundos Bullet, tareas o audio.
- **B está reservado** para volver al launcher. No lo uses para gameplay ni
  llames `ctx.request_exit` para volver: cierra toda la consola.
- Si cambiás cámara/lente, dejá un estado razonable para el launcher.

## Manifest

```toml
id = "mi-juego"
name = "Mi Juego"
version = "0.1.0"
requires_api = "0.1"
description = "Una línea para la plataforma."
locales = ["es"]
default_locale = "es"
players = [1, 4]
modes = ["partida"]
```

- `requires_api` debe ser igual a `API_VERSION` (`0.1`) hoy.
- `players = [mínimo, máximo]`.
- `modes` son etiquetas; todavía no hay selector de modos de plataforma.
- i18n está decidido pero no cableado. UI en español, textos centralizados.
- El launcher usa `name`, `description`, `players` y `modes` del manifest. El
  resto de la metadata de cartelera (rank, event, accent) la pone la plataforma.

## Input del celular

```python
frame = ctx.input_state.frame(0)
if frame is not None:
    aim_x = frame.touch[0].x if frame.touch else 0.5
    if frame.button("A"):
        ...
```

- `A`: acción principal. **B: reservado por la plataforma.**
- `touch`: puntos normalizados `0..1`; puede haber varios.
- `pointer`: apuntado cuando el mando lo soporta.
- `orientation`: `(alpha, beta, gamma)` en grados, relativo a la calibración.
- `gyro`: rad/s. `accel`: m/s².
- El juego debe ser jugable con **touch + A**. Los sensores solo funcionan con
  HTTPS; el modo HTTP por defecto no tiene orientación. No hagas el tilt
  obligatorio.
- Slots 0–3; el hot-seat lo implementa el juego, la plataforma todavía no lo
  administra.
- No uses el teclado como control del juego; el teclado es de la consola.

## Probar y ejecutar

```bash
cd /home/ska/Projects/toxinator
uv run toxinator play mi-juego
uv run toxinator play mi-juego --demo
uv run toxinator play mi-juego --demo --offscreen \
  --screenshot /tmp/mi-juego.png --screenshot-after 3 --seconds 5
uv run toxinator                 # launcher con built-in + juegos externos
uv run pytest
uv run ruff check src tests games
uv run mypy
```

- `--demo` usa `DemoSource` y evita necesitar un celular.
- `--offscreen` sirve para CI/screenshots; no asumas GPU.
- Tests unitarios puros: no importes Panda3D. Tests de integración: `ShowBase`
  headless/offscreen.
- Los tests de un juego externo no están en el `testpaths` del repo; corrélos
  aparte con su propio `PYTHONPATH`/venv o agregá un runner.
- Para física, seguí el patrón de Maldito Pino: paso fijo, acumulador y
  parámetros validados; `PhysicsWorld` de plataforma todavía no está en la API.

## Built-in (solo si el juego va al repo)

La carga está hardcodeada; no hay entry points todavía.

1. `src/toxinator/core/games.py`: loader `_<juego>()`, metadata `GameEntry`,
   rama en `instantiate()`, alta en `load_catalog()`.
2. `src/toxinator/dev/play.py`: `load_game()` usa `find_game()` para built-in y
   `find_external_game()` para externos; no agregues una rama si el juego es
   externo.
3. `pyproject.toml` raíz: workspace member, `testpaths`, `mypy.files`.
4. `tests/unit/test_catalog.py`: actualizá la lista hardcodeada de ids.
5. `uv sync --all-packages`.

El launcher lista hasta cuatro desafíos en la CARTELERA (externos primero, luego
los built-in no instalados). Si hay más, el resto se lanza por id con
`toxinator play <id>`. La cartelera se arma al iniciar: reiniciá la consola si
creás o cambiás un juego.

## Checklist de entrega

- [ ] Juego externo en `~/Projects/toxinator-games/<id>/` (o built-in si va al repo).
- [ ] `manifest.toml` dentro de `src/<module>/`.
- [ ] `create_game(manifest)` en `__init__.py` (externo).
- [ ] Solo imports de `toxinator.api` del runtime.
- [ ] `start/update/stop` implementados, sin bloquear.
- [ ] Escena/HUD en `ctx.scene`/`ctx.ui`; limpieza en `stop`.
- [ ] Jugable con touch + A; tilt opcional; B no se usa.
- [ ] `requires_api = "0.1"`.
- [ ] Probado con `--demo`/`--offscreen`.
- [ ] Tests puros, Ruff y mypy.
- [ ] Skill actualizado si cambió el contrato o la integración.

## Mantenimiento de este skill

Actualizalo en el mismo commit cuando cambie:

- `API_VERSION`, `Game`, `GameContext` o `GameManifest`;
- `ControllerFrame`/`InputState` o los controles de la PWA;
- `external_games.py`, `core/games.py`, `load_game` o el discovery;
- las rutas del directorio externo, tests o comandos;
- cualquier servicio nuevo de `GameContext` (i18n, physics, clock, rng, audio).

Si una regla deja de ser cierta, borrala. No acumules instrucciones viejas.

## Referencias

- [`references/contract-and-lifecycle.md`](references/contract-and-lifecycle.md):
  contrato exacto, lifecycle y servicios disponibles hoy.
- [`references/input-and-controls.md`](references/input-and-controls.md):
  `ControllerFrame`, botones, touch, sensores, HTTP/HTTPS.
- [`references/integration-and-testing.md`](references/integration-and-testing.md):
  directorio externo, template, built-in, tests y comandos.
