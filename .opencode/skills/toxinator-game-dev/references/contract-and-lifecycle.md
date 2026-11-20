# Contrato y ciclo de vida

Fuente de verdad: `src/toxinator/api/game.py`, `src/toxinator/api/input.py`,
`src/toxinator/core/game_host.py` (ciclo de vida, `dt`, límites),
`src/toxinator/core/games.py` (catálogo built-in),
`src/toxinator/core/external_games.py` (juegos externos), y
`src/toxinator/dev/play.py` (carga para `toxinator play`).

## Versión

`API_VERSION = "0.2"`. `GameHost.start()` exige que
`game.manifest.requires_api == API_VERSION`; no hay compatibilidad semver
todavía. Si el contrato cambia, subí la versión y actualizá el host/loader.

## `GameManifest`

```python
@dataclass(frozen=True, slots=True)
class GameManifest:
    id: str
    name: str
    version: str
    requires_api: str
    description: str = ""
    locales: tuple[str, ...] = ("es",)
    default_locale: str = "es"
    players: tuple[int, int] = (1, 4)
    modes: tuple[str, ...] = ("partida",)
    controller_layout: str = "default"
    controller_skin: str = "tokyo-night"
    controller_action: str = "Acción"
    controller_back: str = "Volver"
    controller_hint: str = ""
    art_motif: str = "auto"
```

`load_manifest(text_or_path)` parsea TOML y normaliza `players` a una tupla de
dos enteros. El campo `id` es la clave para `toxinator play <id>`. La sección
opcional `[controller]` define el layout, la skin y las etiquetas del mando para
ese juego; se envía al celular al lanzarlo. La sección `[art]` elige el prop del
diorama (`pin`, `flag`, `paddle`, `pong`, `star`, `heart`, `coin`, `cube` o
`auto`).

## `GameContext`

```python
@dataclass
class GameContext:
    base: Any
    scene: Any
    ui: Any
    input_state: InputState
    phone: PhoneService
    locale: str = "es"
    request_exit: Callable[[], None] | None = None
```

Estos son los campos actuales. No hay `ctx.audio`, `ctx.assets`,
`ctx.settings`, `ctx.save`, `ctx.i18n`, `ctx.clock`, `ctx.rng`, `ctx.physics`
ni `ctx.events`, aunque estén decididos en ADRs. No inventes esos servicios: si
los necesitás, primero se agregan a la API y al host. `ctx.phone` es solo
feedback del celular (vibración/tonos), no audio de la consola.

- `scene`: raíz del juego en `render` (`base.render.attach_new_node(...)`).
- `ui`: raíz del juego en `aspect2d`.
- `input_state`: último snapshot del `InputHub`, actualizado por `GameHost` en
  cada frame.
- `phone`: feedback opcional en el teléfono.
- `locale`: hoy `"es"`; i18n no está cableado.
- `request_exit`: apunta a `base.userExit`. **No lo uses para volver al
  launcher**: cierra toda la consola. El back lo maneja la plataforma.

## `PhoneService`

```python
class PhoneService(Protocol):
    def vibrate(self, pattern: int | Sequence[int], slot: int | None = None) -> None: ...
    def tone(
        self,
        frequency: float,
        duration_ms: int,
        *,
        volume: float = 0.35,
        slot: int | None = None,
    ) -> None: ...
    def stop(self, slot: int | None = None) -> None: ...
```

- `slot=None` manda a todos los celulares; un slot apunta a un jugador.
- `vibrate` usa milisegundos y patrón on/off. Android sí; iPhone/Safari no
  expone vibración web.
- `tone` reproduce un seno corto con Web Audio. El audio necesita un gesto del
  usuario para desbloquearse; funciona en HTTP.
- `stop` corta audio y vibración.
- Si no hay celular, la implementación es no-op. El juego no debe bloquearse ni
  asumir que el feedback existe.

## `Game`

```python
class Game(Protocol):
    manifest: GameManifest

    def start(self, ctx: GameContext) -> None: ...
    def update(self, dt: float) -> None: ...
    def stop(self) -> None: ...
```

- `start` construye escena, luces, cámara y HUD. No crea `ShowBase` ni ventana.
- `update` corre cada frame; `dt` ya está limitado a `0.0..0.1`.
- `stop` limpia lo que el host no puede limpiar: mundos Bullet, tareas, audio,
  referencias, estado de cámara/lente.

## `GameHost`

Flujo real:

1. Crea `scene` y `ui` como hijos de `render` y `aspect2d`.
2. Construye `GameContext` con un `InputState` vacío.
3. Verifica `requires_api` exacto.
4. Llama `game.start(ctx)`.
5. Cada frame: `ctx.input_state = input_hub.poll()` y `game.update(dt)`.
6. En `stop`: llama `game.stop()`, atrapa excepciones y remueve `scene`/`ui`.

Los juegos son in-process. Un crash duro se lleva la consola; por eso `update`
no debe bloquear ni lanzar excepciones no controladas.

## Frontera y dependencias

- Un juego solo importa `toxinator.api` del runtime. Para Panda3D puede importar
  `panda3d.*` y `direct.*`; para sus propias reglas, sus módulos.
- No importes `toxinator.core`, `toxinator.input`, `toxinator.dev`,
  `toxinator.launcher` ni `toxinator.physics`.
- No leas input directo de Panda3D ni abras WebSocket/red. El celular, el
  launcher y el servidor son de la plataforma.
- No uses `base.taskMgr` para lógica de juego si podés hacerlo en `update`;
  las tareas extra son más difíciles de limpiar y de testear.
- Assets originales; sin marcas, personajes ni assets de Nintendo. Respetá las
  licencias de fuentes, sonidos y modelos.

## Cámara y escena

La escena del juego se elimina al salir, pero el estado de cámara/lente es
compartido por el `ShowBase`. Si el juego mueve la cámara, dejá una posición
razonable o restaurá la del launcher en `stop`. Las luces deben colgar de
`ctx.scene` para que se limpien con la raíz.

## Juegos externos vs built-in

- **Externo**: el cargador agrega `src/` al `sys.path`, importa el paquete y
  llama `create_game(manifest)`. El launcher lo lista en la biblioteca usando
  `name`, `description`, `players` y `modes` del manifest.
- **Built-in**: se agrega a `core/games.py` y al workspace; aparece en la
  biblioteca de ejemplo. Es el camino de Maldito Pino y de los ejemplos oficiales.
