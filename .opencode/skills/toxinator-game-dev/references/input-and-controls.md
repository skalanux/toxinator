# Input y controles

Fuente de verdad: `src/toxinator/api/input.py`, `src/toxinator/input/hub.py`,
`src/toxinator/input/keyboard.py`, `src/toxinator/input/phone/registry.py` y
`controller-web/app.js`.

## Movimiento primero, touch como apoyo

La entrada más divertida de Toxinator es el movimiento: `orientation`
(`alpha`/`beta`/`gamma`, yaw/pitch/roll), `gyro` y `accel`. Un juego debería
diseñar su gesto principal alrededor de inclinar, girar, lanzar, balancear o
acelerar el teléfono. El touch es un excelente apoyo para apuntar, cargar o
confirmar, y es el fallback obligatorio, pero no debería ser el único esquema si
el gesto se puede mapear a movimiento.

- El gesto principal tiene que funcionar con movimiento cuando hay sensores.
- El juego tiene que seguir siendo jugable con **stick + touch + ×** sin sensores.
- No bloquees el arranque ni pidas calibración obligatoria: si no llega
  orientación, seguí con `pointer`/`move`.
- Los sensores solo funcionan en HTTPS. La PWA intenta activarlos al conectar;
  si el navegador exige permiso (iOS), el primer toque lo pide y el pie muestra
  **SENSORES · TOCÁ**. No prometas movimiento en HTTP.
- Un juego touch-first es válido (punteros, grillas, cartas), pero si el gesto
  principal puede ser movimiento, usalo.

## `InputState`

```python
@dataclass(frozen=True, slots=True)
class InputState:
    timestamp: float
    frames: Mapping[int, ControllerFrame]
    controllers: Mapping[int, ControllerInfo]

    def frame(self, slot: int) -> ControllerFrame | None: ...
    def controller(self, slot: int) -> ControllerInfo | None: ...
    def primary_slot(self) -> int | None: ...
    def primary_frame(self) -> ControllerFrame | None: ...
    def primary_controller(self) -> ControllerInfo | None: ...
```

- Un juego de un jugador usa `primary_frame()`: prefiere el celular y cae al
  teclado/mouse si no hay teléfono. No hardcodees `frame(0)`.
- Hay hasta 4 slots de teléfono (0–3). El teclado/mouse usa el slot 4 por
  defecto (`--keyboard-slot`).
- El juego lee `ctx.input_state`; no lee el WebSocket ni el celular directo.

## `ControllerFrame`

```python
@dataclass(frozen=True, slots=True)
class ControllerFrame:
    controller_id: str
    timestamp: float
    buttons: frozenset[str]
    axes: Mapping[str, float]
    accel: tuple[float, float, float]
    gyro: tuple[float, float, float]
    orientation: tuple[float, float, float]
    pointer: tuple[float, float] | None
    touch: tuple[TouchPoint, ...]
```

- Botones canónicos: `cross`, `circle`, `square`, `triangle`, `options`, `l1`,
  `r1`. `button("cross")` es la acción; `button("circle")` vuelve.
- Compatibilidad: apretar × también emite `A`, y ○ emite `B`; los alias se
  retiran en API `0.4`. Código nuevo usa los nombres canónicos.
- `pointer`: apuntado normalizado `0..1`, disponible con dedo, mouse o teclado.
  Es la forma recomendada de apuntar; no dependas de `touch[0]`.
- `touch`: `TouchPoint(id, x, y, pressure)` normalizado `0..1`; puede haber
  varios.
- `axes["move_x"]` / `axes["move_y"]`: stick izquierdo, `-1..1`, `+y` arriba.
- `orientation`: `(alpha, beta, gamma)` en grados (`yaw`, `pitch`, `roll`),
  relativo a la calibración neutra del celular. No es orientación absoluta.
- `gyro`: rad/s. `accel`: m/s².

## Controles de la PWA

- **LAUNCHER**: stick izquierdo (o mouse), **× / ELEGIR**, **○ / ATRÁS**. El
  launcher usa el stick y el puntero como navegación espacial; no usa sensores.
- **JUEGO**: × ○ □ △, `options`, `L1`/`R1`, stick izquierdo, zona táctil derecha,
  calibración, sensores y panel del juego.
- La zona táctil es absoluta: la posición del dedo es `pointer` (`0..1`).
- El stick vuelve al centro al soltar y tiene deadzone; usá `move_x`/`move_y`.
- El mando funciona en **landscape y vertical**; el perfil puede pedir una
  orientación y la PWA muestra un aviso si el teléfono está al revés.
- **× es la acción del juego.** **○ es de la plataforma**: vuelve al launcher o
  cierra el overlay actual. Un juego no debe usar ○ para gameplay ni intentar
  interceptarlo.
- `options` es del juego (pausa propia). La plataforma no lo intercepta.
- La PWA muestra el panel del juego (imagen estática) y, si el perfil lo pide,
  el botón de cámara. El panel no captura input.
- El teclado/mouse es un **simulador** para manejar la consola y jugar sin
  celular: flechas/WASD = stick, Enter/J = ×, Esc/K = ○, L = □, I = △, Tab =
  `options`, Q/E = L1/R1. No es un requisito del juego, pero sirve para testear.

### Perfil `[controller]`

```toml
[controller]
layout = "motion"          # default | motion | touch
skin = "toxinator"         # única skin de la v1
orientation = "auto"       # auto | portrait | landscape
hint = "Incliná para apuntar"
camera = false

[controller.labels]
cross = "Tirar"
circle = "Volver"
square = ""
triangle = ""
options = ""
l1 = ""
r1 = ""

[controller.panel]         # opcional
title = "Mapa"
image = "assets/mapa.png"  # relativo a los assets del paquete
fit = "contain"            # contain | cover | stretch
```

- `layout` cambia el énfasis visual (movimiento, touch o mixto), no la anatomía.
- `orientation` fuerza el layout; `auto` sigue al teléfono. El jugador puede
  bloquear la orientación desde los ajustes.
- `labels` cambia las etiquetas visibles; `action`/`back` se mantienen por
  compatibilidad. **○ sigue siendo la plataforma.**
- `camera = true` muestra el botón de foto. Requiere HTTPS.
- `panel` muestra una imagen estática; el juego puede cambiarla en runtime:

```python
ctx.phone.panel(title="Mapa", image="assets/mapa.png", fit="cover")
ctx.phone.clear_panel()
```

- Sin `[controller]`, se usan `default`, `toxinator`, `auto`, `Acción` y
  `Volver`.

## Feedback del celular

`ctx.phone` permite vibrar, reproducir tonos y manejar el panel:

```python
if frame.button("cross"):
    ctx.phone.vibrate([20, 30, 40], slot=0)
    ctx.phone.tone(880, 80, volume=0.35, slot=0)
```

- `slot=None` manda a todos; un slot apunta a un jugador.
- `vibrate` recibe un entero o un patrón on/off en milisegundos. Android
  Chrome/Samsung lo soporta; iPhone/Safari no expone vibración web y Firefox
  Android la tiene deshabilitada (puede devolver `true` sin vibrar).
- `tone` es un seno corto por Web Audio. El audio necesita un gesto del usuario
  para desbloquearse; el toque de conexión/calibración alcanza. Funciona en HTTP.
- `stop(slot=None)` corta audio y vibración.
- `panel(...)` / `clear_panel()` son no-op sin celular.
- Si no hay celular, todo es no-op. El feedback es opcional: no bloquees el
  gameplay.
- La PWA muestra un aviso **ACTIVAR SONIDO Y VIBRACIÓN** al entrar al juego;
  ese toque desbloquea y prueba audio/vibración. No hace falta que el juego
  dibuje su propio botón.
- `ControllerInfo.capabilities` incluye `haptics`, `speaker`, `camera` y `panel`
  para los celulares.

## HTTP vs HTTPS

- El modo por defecto es **HTTP/WS**, sin certificado.
- `DeviceMotionEvent`/`DeviceOrientationEvent` requieren **secure context**
  (HTTPS o localhost). En HTTP los listeners existen pero no se disparan.
- Por eso un juego debe ser jugable con **stick + touch + ×**. El movimiento es
  la entrada preferida cuando está disponible, pero es opcional.
- `--https` habilita sensores y cámara; el usuario debe aceptar el certificado o
  instalar una CA de confianza. En HTTPS los sensores arrancan solos, salvo que
  el navegador exija un gesto de permiso.
- La foto de avatar y el escaneo de QR requieren HTTPS.

## Patrones útiles

- **Apuntar**: usá `frame.pointer`; el touch y el mouse lo llenan. El movimiento
  es el gesto principal; el puntero es el ajuste fino.
- **Cargar**: × mantenida; soltar dispara; usar un estado `charge`/`aim`.
- **Efecto**: `orientation[2]` (gamma) relativa; opcional y con deadzone.
- **Girar**: `alpha` o `gyro[2]` para rotación; integrá con `dt` si usás gyro.
- **Balancear**: `accel` + `gyro` para detectar el gesto; × para confirmar.
- **Confirmar**: × en el menú; no ○.
- **Sin sensores**: un slider/drag horizontal o el stick para el efecto; no
  bloquees el juego si `orientation` es cero.
- **Calibración**: la plataforma ya entrega orientación relativa al neutro; no
  recalibres desde el juego.

## Hot-seat

Los slots 0–3 existen, pero la plataforma no administra turnos, pausas ni
asignación de jugadores. Si el juego es 1–4, implementá el hot-seat en el juego
y leé el `frame(slot)` correspondiente. El manifest declara `players`.

## Pruebas de input

`--demo` inyecta un `DemoSource` en P1 con movimiento sintético; sirve para ver
que el juego reacciona sin celular:

```bash
uv run toxinator play mi-juego --demo
```

Para probar los controles nuevos, usá la PWA; para jugar sin celular, `toxinator
play mi-juego` ya incluye el simulador de teclado/mouse (`--no-keyboard` lo
apaga). Para tests unitarios, construí `ControllerFrame`/`InputState` a mano; no
necesitás Panda3D.
