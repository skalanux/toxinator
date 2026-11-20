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

> **Estado del contrato**: API `0.2` (match exacto). Hay dos caminos: juegos
> **externos** en `~/Projects/toxinator-games` (recomendado) y juegos
> **built-in** en `games/` del repo (solo para el ejemplo de la plataforma).
> Los externos aparecen en la **biblioteca** del launcher al iniciar y se lanzan
> con A/ENTER; también con `toxinator play <id>`.
> i18n, audio, assets, settings, save, clock, rng y PhysicsWorld **no** están
> expuestos en `GameContext` aunque estén decididos en ADRs.
> Última revisión: 2026-11-19.

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
| **Externo** | `~/Projects/toxinator-games/<juego>/` | escaneo de `src/*/manifest.toml`, `create_game(manifest)` y biblioteca del launcher | juegos nuevos, prototipos, repos separados |
| **Built-in** | `games/<juego>/` del repo | catálogo hardcodeado en `core/games.py` | ejemplo oficial, tests de plataforma |

Para juegos nuevos, usá el camino externo. Mantené el repo de la plataforma
limpio de contenido de juego. Maldito Pino queda como referencia built-in.

## Flujo externo (recomendado)

1. Creá el esqueleto y instalalo:
   ```bash
   cd /home/ska/Projects/toxinator
   uv run toxinator new mi-juego          # crea ./mi-juego/
   uv run toxinator install mi-juego      # symlink en ~/Projects/toxinator-games
   ```
   `new` acepta `--dir <padre>` (por defecto, el directorio actual) y
   `--name "Mi Juego"`. Genera `src/mi_juego/` con `manifest.toml`,
   `__init__.py`, `game.py`, más `pyproject.toml`, `README.md` y una copia del
   skill en `.opencode/skills/toxinator-game-dev/` (para que el agente lo tenga
   disponible dentro del juego).
   `install` acepta la ruta del juego (por defecto, `.`) y `--force` para
   reemplazar un symlink; nunca pisa un directorio real.
2. Editá `src/mi_juego/manifest.toml` (`id`, `name`, etc.) y el paquete.
3. Implementá `src/mi_juego/game.py` y `create_game()` en `__init__.py`.
4. Ejecutá:
   ```bash
   cd /home/ska/Projects/toxinator
   uv run toxinator play mi-juego
   uv run toxinator play mi-juego --demo
   ```
5. Para verlo en la consola, reiniciá el launcher:
   ```bash
   uv run toxinator
   ```
   El juego aparece en **Tus juegos** y en el **Catálogo**, y se lanza con A/ENTER.

`install` sigue siendo un symlink al directorio, no una copia ni un paquete
Python instalado: el juego usa el venv de la consola. El nombre del symlink es
el `id` del manifest y el directorio destino es `games_dir()`, así que
`TOXINATOR_GAMES_DIR` también aplica al instalador.

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
requires_api = "0.2"
description = "Una línea para la plataforma."
locales = ["es"]
default_locale = "es"
players = [1, 4]
modes = ["partida"]

[controller]
layout = "motion"
skin = "tokyo-night"
action = "Tirar"
back = "Volver"
hint = "Incliná para apuntar"

[art]
motif = "pin"
```

- `requires_api` debe ser igual a `API_VERSION` (`0.2`) hoy.
- `players = [mínimo, máximo]`.
- `modes` son etiquetas; todavía no hay selector de modos de plataforma.
- i18n está decidido pero no cableado. UI en español, textos centralizados.
- El launcher usa `name`, `description`, `players` y `modes` del manifest. El
  resto de la metadata de catálogo (accent, arte) la pone la plataforma.
- `[controller]` es opcional. `layout` puede ser `default`, `motion` o `touch`;
  `skin` puede ser `tokyo-night`, `tokyo-storm`, `tokyo-moon` o `tokyo-mint`.
  `action`/`back` cambian las etiquetas de A/B y `hint` es la ayuda que muestra
  el celular. **B sigue reservado por la plataforma.**
- `[art]` es opcional. `motif` elige el prop del diorama: `pin`, `flag`,
  `paddle`, `pong`, `star`, `heart`, `coin` o `cube`. `auto` (default) lo deriva
  del id del juego.

## Input del celular

**Movimiento primero.** El acelerómetro, el gyro y la orientación
(`alpha`/`beta`/`gamma`, es decir yaw/pitch/roll) son la entrada más divertida de
la consola. Diseñá el gesto principal alrededor de inclinar, girar o mover el
teléfono. El touch es un buen apoyo y sirve para apuntar, cargar o confirmar,
pero no debería ser el único esquema si el juego puede aprovechar el movimiento.

- El gesto principal debería poder hacerse con movimiento: apuntar, inclinar,
  girar, lanzar, balancear, acelerar.
- El touch queda como apoyo y como fallback. Un juego de puntero puede ser
  touch-first, pero si el gesto se puede mapear a movimiento, hacelo.
- Los sensores son **opcionales**: solo funcionan en HTTPS y el usuario tiene
  que habilitarlos. El juego debe seguir siendo jugable con **touch + A** sin
  bloquearse ni mostrar errores.
- No hagas el tilt obligatorio para arrancar. Detectá el primer frame con
  orientación/gyro distinto de cero y activá el modo movimiento; si no llega,
  seguí con touch.

```python
frame = ctx.input_state.frame(0)
if frame is not None:
    yaw, pitch, roll = frame.orientation
    touch_x = frame.touch[0].x if frame.touch else 0.5
    has_motion = abs(pitch) + abs(roll) > 1.0
    aim_x = max(0.0, min(1.0, 0.5 + roll / 45.0)) if has_motion else touch_x
    if frame.button("A"):
        ...
```

- `A`: acción principal. **B: reservado por la plataforma.**
- `touch`: puntos normalizados `0..1`; puede haber varios.
- `pointer`: apuntado cuando el mando lo soporta.
- `orientation`: `(alpha, beta, gamma)` en grados, relativo a la calibración.
- `gyro`: rad/s. `accel`: m/s².
- Slots 0–3; el hot-seat lo implementa el juego, la plataforma todavía no lo
  administra.
- No uses el teclado como control del juego; el teclado es de la consola.

### Feedback del celular

`GameContext.phone` ofrece feedback opcional en el teléfono:

```python
if frame.button("A"):
    ctx.phone.vibrate([20, 30, 40], slot=0)
    ctx.phone.tone(880, 80, volume=0.35, slot=0)
```

- `vibrate(pattern, slot=None)`: patrón en milisegundos (vibra/pausa/vibra).
  `slot=None` manda a todos. **Android Chrome/Samsung sí; iPhone/Safari no
  expone vibración web y Firefox Android la tiene deshabilitada.**
- `tone(frequency_hz, duration_ms, *, volume=0.35, slot=None)`: tono corto por
  el parlante usando Web Audio.
- `stop(slot=None)`: corta tonos y vibración.
- El audio necesita un gesto del usuario para desbloquearse; el toque de
  conexión/calibración alcanza. En HTTP funciona; la cámara no.
- El feedback es **opcional**: si el celular no lo soporta, el juego tiene que
  seguir funcionando igual. No bloquees el gameplay esperándolo.
- Usalo para impactos, puntos, tiros y confirmaciones, no para vibrar sin parar.
- Las capacidades `haptics` y `speaker` aparecen en `ControllerInfo.capabilities`
  cuando el mando es un celular.

### Layouts y skins del mando

El perfil `[controller]` del manifest viaja al celular al lanzar el juego:

| Layout | Cuándo usarlo |
|---|---|
| `motion` | El gesto principal es inclinar/girar. El celular agranda β/γ y deja el touch como apoyo. **Recomendado.** |
| `touch` | El gesto principal es arrastrar/apuntar. El touchpad gana protagonismo. |
| `default` | Juego mixto o sin preferencia. |

Skins: `tokyo-night`, `tokyo-storm`, `tokyo-moon`, `tokyo-mint`. La skin del
perfil es el default del juego; el jugador puede cambiarla desde el botón
**Skin** del celular, que abre un selector visual, y su elección se recuerda. Las
etiquetas `action`/`back` y el `hint` se muestran en el mando. El botón
**Avanzado** revela el readout técnico y la calibración; por defecto el mando se
mantiene simple.

## Probar y ejecutar

```bash
cd /home/ska/Projects/toxinator
uv run toxinator play mi-juego
uv run toxinator play mi-juego --demo
uv run toxinator play mi-juego --cloudflare   # HTTPS válido sin tocar la CA
uv run toxinator play mi-juego --demo --offscreen \
  --screenshot /tmp/mi-juego.png --screenshot-after 3 --seconds 5
uv run toxinator                 # launcher con built-in + juegos externos
uv run pytest
uv run ruff check src tests games
uv run mypy
```

- `--demo` usa `DemoSource` y evita necesitar un celular.
- `--cloudflare` crea un Quick Tunnel HTTPS con `cloudflared`; sirve para
  sensores/cámara/PWA sin instalar una CA en el teléfono. Necesita internet.
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

La pantalla de inicio muestra hasta cinco juegos en **Tus juegos**; el resto
vive en el **Catálogo**, con filtros y paginación. Todos se lanzan con A/ENTER o
desde el celular, y también por id con `toxinator play <id>`. La biblioteca se
arma al iniciar: reiniciá la consola si creás o cambiás un juego.

## Checklist de entrega

- [ ] Juego externo en `~/Projects/toxinator-games/<id>/` o symlink creado con
      `toxinator install` (o built-in si va al repo).
- [ ] `manifest.toml` dentro de `src/<module>/`.
- [ ] `create_game(manifest)` en `__init__.py` (externo).
- [ ] Solo imports de `toxinator.api` del runtime.
- [ ] `start/update/stop` implementados, sin bloquear.
- [ ] Escena/HUD en `ctx.scene`/`ctx.ui`; limpieza en `stop`.
- [ ] Diseñado **motion-first**: el gesto principal usa orientación/giro/accel;
      touch + A como apoyo y fallback; B no se usa.
- [ ] Perfil `[controller]` declarado (layout, skin, action, hint) o defaults
      conscientes.
- [ ] Feedback opcional probado: vibración/tono no bloquea si no está
      disponible.
- [ ] `requires_api = "0.2"`.
- [ ] Probado con `--demo`/`--offscreen`.
- [ ] Tests puros, Ruff y mypy.
- [ ] Skill actualizado si cambió el contrato o la integración.

## Mantenimiento de este skill

Actualizalo en el mismo commit cuando cambie:

- `API_VERSION`, `Game`, `GameContext` o `GameManifest`;
- `ControllerFrame`/`InputState` o los controles/layouts/skins de la PWA;
- `PhoneService`/feedback del celular o el protocolo del servidor;
- `external_games.py`, `core/games.py`, `load_game`, el discovery o
  `dev/projects.py` (comandos `new`/`install`);
- las rutas del directorio externo, tests o comandos;
- cualquier servicio nuevo de `GameContext` (i18n, physics, clock, rng, audio).

Si una regla deja de ser cierta, borrala. No acumules instrucciones viejas.

`toxinator new` copia este skill dentro de cada juego nuevo. Al cambiarlo, los
proyectos ya creados quedan con la copia vieja: `new` solo escribe en
directorios nuevos o vacíos. Si un juego existente necesita la versión nueva,
copiá `.opencode/skills/toxinator-game-dev/` a mano.

## Referencias

- [`references/contract-and-lifecycle.md`](references/contract-and-lifecycle.md):
  contrato exacto, lifecycle y servicios disponibles hoy.
- [`references/input-and-controls.md`](references/input-and-controls.md):
  `ControllerFrame`, botones, touch, sensores, HTTP/HTTPS.
- [`references/integration-and-testing.md`](references/integration-and-testing.md):
  directorio externo, template, built-in, tests y comandos.
