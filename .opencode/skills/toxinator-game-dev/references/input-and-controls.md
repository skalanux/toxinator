# Input y controles

Fuente de verdad: `src/toxinator/api/input.py`, `src/toxinator/input/hub.py`,
`src/toxinator/input/phone/registry.py` y `controller-web/app.js`.

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
- `orientation`: `(alpha, beta, gamma)` en grados, relativo a la calibración
  neutra del celular. No es orientación absoluta.
- `gyro`: rad/s. `accel`: m/s².
- `axes`: mapa de ejes para mandos que los expongan.

## Controles de la PWA

- **LAUNCHER**: joystick táctil, **A / ELEGIR**, **B / ATRÁS**. El launcher usa
  el touch como navegación espacial; no usa sensores.
- **JUEGO**: touchpad de apuntado, **A / ACCIÓN**, **B / VOLVER**, calibración y
  sensores.
- **B es de la plataforma**: vuelve al launcher o cierra el overlay actual. Un
  juego no debe usarlo para gameplay ni intentar interceptarlo.
- **A** es la acción del juego. No hay teclado para gameplay: el teclado es de
  la consola.

## HTTP vs HTTPS

- El modo por defecto es **HTTP/WS**, sin certificado.
- `DeviceMotionEvent`/`DeviceOrientationEvent` requieren **secure context**
  (HTTPS o localhost). En HTTP los listeners existen pero no se disparan.
- Por eso un juego debe ser jugable con **touch + A**. El tilt/efecto por
  sensores es opcional; si no hay sensores, usá un control táctil alternativo o
  ignorá el efecto.
- `--https` habilita sensores/cámara; el usuario debe aceptar el certificado o
  instalar una CA de confianza.
- El PWA en modo juego muestra β/γ/ACC/RTT; en HTTP pueden quedar en cero.

## Patrones útiles

- **Apuntar**: `aim = frame.touch[0].x` con clamp a un rango de juego.
- **Cargar**: A mantenida; soltar dispara; usar un estado `charge`/`aim`.
- **Efecto**: `orientation[2]` (gamma) relativa; opcional y con deadzone.
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
