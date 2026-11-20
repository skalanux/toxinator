# Input y controles

Fuente de verdad: `src/toxinator/api/input.py`, `src/toxinator/input/hub.py`,
`src/toxinator/input/phone/registry.py` y `controller-web/app.js`.

## Movimiento primero, touch como apoyo

La entrada más divertida de Toxinator es el movimiento: `orientation`
(`alpha`/`beta`/`gamma`, yaw/pitch/roll), `gyro` y `accel`. Un juego debería
diseñar su gesto principal alrededor de inclinar, girar, lanzar, balancear o
acelerar el teléfono. El touch es un excelente apoyo para apuntar, cargar o
confirmar, y es el fallback obligatorio, pero no debería ser el único esquema si
el gesto se puede mapear a movimiento.

- El gesto principal tiene que funcionar con movimiento cuando hay sensores.
- El juego tiene que seguir siendo jugable con **touch + A** sin sensores.
- No bloquees el arranque ni pidas calibración obligatoria: si no llega
  orientación, seguí con touch.
- Los sensores solo funcionan en HTTPS y con permiso del usuario. No prometas
  movimiento en HTTP.
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
    @property
    def connected_slots(self) -> tuple[int, ...]: ...
```

Hay hasta 4 slots. El juego lee `ctx.input_state.frame(slot)`; no lee el
WebSocket ni el celular directo.

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

- `button("A")`, `button("B")`.
- `touch`: `TouchPoint(id, x, y, pressure)` normalizado `0..1`.
- `pointer`: posición de apuntado si el mando la expone.
- `orientation`: `(alpha, beta, gamma)` en grados (`yaw`, `pitch`, `roll`),
  relativo a la calibración neutra del celular. No es orientación absoluta.
- `gyro`: rad/s. `accel`: m/s².
- `axes`: mapa de ejes para mandos que los expongan.

## Controles de la PWA

- **LAUNCHER**: joystick táctil, **A / ELEGIR**, **B / ATRÁS**. El launcher usa
  el touch como navegación espacial; no usa sensores. El joystick es relativo y
  no muestra readout ni calibración salvo que actives **Avanzado**.
- **JUEGO**: touchpad, **A / ACCIÓN**, **B / VOLVER**, calibración y sensores.
  El readout técnico y los controles de sensores quedan detrás de **Avanzado**.
- El manifest puede elegir el **layout** del mando:
  - `motion`: agranda β/γ y deja el touch como apoyo. Recomendado para juegos
    con gesto principal de inclinación/giro.
  - `touch`: da protagonismo al touchpad para juegos de puntero/arrastre.
  - `default`: layout mixto.
- El manifest también puede elegir la **skin** (`tokyo-night`, `tokyo-storm`,
  `tokyo-moon`, `tokyo-mint`) y las etiquetas `action`/`back`/`hint`. El jugador
  puede cambiar la skin desde el botón **Skin** del celular, que abre un selector
  visual; su elección se recuerda.
- **Avanzado** es un toggle del mando: oculta por defecto el readout β/γ/ACC/RTT,
  el estado de sensores y **Calibrar / Activar sensores**. El juego no necesita
  tocar ese toggle.
- **B es de la plataforma**: vuelve al launcher o cierra el overlay actual. Un
  juego no debe usarlo para gameplay ni intentar interceptarlo.
- **A** es la acción del juego. No hay teclado para gameplay: el teclado es de
  la consola.

### Perfil `[controller]`

```toml
[controller]
layout = "motion"
skin = "tokyo-night"
action = "Tirar"
back = "Volver"
hint = "Incliná para apuntar"
```

El launcher envía este perfil al celular al lanzar el juego. `action`/`back` solo
cambian las etiquetas visibles; **B sigue siendo la plataforma**. `hint` es la
ayuda corta que aparece en el mando. Si el manifest no trae `[controller]`, se
usan `default`, `tokyo-night`, `Acción` y `Volver`.

## Feedback del celular

`ctx.phone` permite vibrar y reproducir tonos en el teléfono:

```python
if frame.button("A"):
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
- Si no hay celular, es no-op. El feedback es opcional: no bloquees el gameplay.
- La PWA muestra un aviso **ACTIVAR SONIDO Y VIBRACIÓN** al entrar al juego;
  ese toque desbloquea y prueba audio/vibración. No hace falta que el juego
  dibuje su propio botón.
- `ControllerInfo.capabilities` incluye `haptics` y `speaker` para los celulares.

## HTTP vs HTTPS

- El modo por defecto es **HTTP/WS**, sin certificado.
- `DeviceMotionEvent`/`DeviceOrientationEvent` requieren **secure context**
  (HTTPS o localhost). En HTTP los listeners existen pero no se disparan.
- Por eso un juego debe ser jugable con **touch + A**. El movimiento es la
  entrada preferida cuando está disponible, pero es opcional: si no hay
  sensores, usá un control táctil alternativo o ignorá el efecto.
- `--https` habilita sensores/cámara; el usuario debe aceptar el certificado o
  instalar una CA de confianza.
- El PWA en modo juego muestra β/γ/ACC/RTT; en HTTP pueden quedar en cero.

## Patrones útiles

- **Apuntar**: combiná `orientation[1]`/`orientation[2]` con `touch[0]` como
  fallback. El movimiento es el gesto principal; el touch es el ajuste fino.
- **Cargar**: A mantenida; soltar dispara; usar un estado `charge`/`aim`.
- **Efecto**: `orientation[2]` (gamma) relativa; opcional y con deadzone.
- **Girar**: `alpha` o `gyro[2]` para rotación; integrá con `dt` si usás gyro.
- **Balancear**: `accel` + `gyro` para detectar el gesto; A para confirmar.
- **Confirmar**: A en el menú; no B.
- **Sin sensores**: un slider/drag horizontal o un segundo touch para el efecto;
  no bloquees el juego si `orientation` es cero.
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

Para probar A/B/touch reales, usá la PWA. Para tests unitarios, construí
`ControllerFrame`/`InputState` a mano; no necesitás Panda3D.
