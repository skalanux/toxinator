# Gestos del mando: contrato, catálogo y laboratorio

Spec de implementación de los gestos de plataforma. La decisión está en
[ADR-0010](../adr/0010-gesture-recognizer.md). Este documento fija el contrato
que comparten la PWA, el reconocedor, el `InputHub`, la API y los juegos.

> **Estado**: milestones 1 (núcleo), 2 (completo) y 3 (laboratorio/trazas)
> implementados; queda 4 (migración de Maldito Pino).

## Alcance

Entra en la v1:

- Reconocedor en Python sobre `ControllerFrame`, uno por slot y fuente.
- Posturas `tilt`, `steer` y `aim`; eventos `flick`, `swing`, `twist`, `shake`
  y `flip`.
- Declaración por juego en `[controller] gestures` y labels para el hint.
- Recentrar en caliente, desde el juego y desde el celular.
- Simulador de teclado/mouse que emite los mismos gestos.
- Trazas, tests sintéticos, suite de falsos positivos y laboratorio
  `toxinator dev gestures`.

No entra: visión por cámara, seguimiento de marcadores, clasificador de ML,
barra IR, soporte iOS ni editor de gestos por el jugador. El Wiimote queda fuera
del roadmap ([ADR-0007](../adr/0007-phone-controller-v2.md)).

## Tres cosas distintas

| Concepto | Naturaleza | Llega por | Ejemplo |
| --- | --- | --- | --- |
| **Postura** | analógica, continua | `frame.axes` | `tilt_x`, `steer`, `aim_x` |
| **Evento** | discreta, un instante | `InputState.gestures` | `flick` arriba, `twist` horario |
| **Puntero** | posición absoluta | `frame.pointer` | touch, mouse o `aim` |

La postura no se "consume": el juego la lee cada frame. El evento sí: el
`InputHub` lo entrega una sola vez. Un gesto declarado puede ser postura,
evento o ambos (`aim` es postura y puntero).

```python
@dataclass(frozen=True, slots=True)
class Gesture:
    slot: int
    controller_id: str
    name: str          # "flick", "swing", ...
    direction: str     # "up" | "down" | "left" | "right" | "cw" | "ccw" | "none"
    intensity: float   # 0..1
    timestamp: float
```

`InputState` expone `gestures: tuple[Gesture, ...]`, más
`gestures_for(slot)` y `gesture(name)` como atajos. `ControllerFrame` no lleva
eventos: el frame describe el estado, el `InputState` describe lo que pasó.

## Dónde corre

```text
PWA ──state 60 Hz──► PhoneRegistry.build_frame ──► GestureRecognizer.update
                                                        │
                                   posturas ◄───────────┤
                                                        │
                                   eventos  ──► cola por slot
                                                        │
InputHub.poll ◄── PhoneSource.poll ◄────────────────────┘
     │
     ├─► frame con posturas
     └─► InputState.gestures  (solo gestos declarados)
```

Reglas:

- El reconocedor consume **frames normalizados**, no payloads crudos. Así el
  replay de una traza reproduce exactamente la misma detección.
- Hay una instancia por slot y fuente (`PhoneConnection`, `KeyboardMouseSource`,
  `ReplaySource`). No hay estado global.
- La detección corre en el hilo de red del celular (o en el poll del simulador),
  no en el game loop.
- El `InputHub` acumula los eventos de cada slot y los drena en cada `poll()`.
  Un frame pisado entre dos polls **no pierde** un gesto.
- Los eventos del celular se drenan con `PhoneRegistry.take_gestures(slot)` bajo
  lock: `snapshot()` devuelve copias y no sirve para consumir la cola.
- Cola acotada a 32 eventos por slot; si desborda, se descartan los más viejos y
  se loguea una vez. Se vacía al desconectar, al calibrar y al cambiar de modo.

### Garantías de entrega

- Cada evento se entrega exactamente una vez al game loop.
- Orden estable por timestamp; los empates conservan el orden de detección.
- `InputState.gestures` son los eventos **desde el poll anterior**, no desde el
  inicio de la partida.
- El conjunto activo se fija con `InputHub.set_enabled_gestures(names)`, que el
  host llama al lanzar un juego con el `gestures` del manifest. Sin llamada, el
  hub entrega todo (dev y tests). Un juego sin gestos declarados recibe las
  posturas pero ningún evento.

## Frame y protocolo

`ControllerFrame` suma dos campos con default, para no romper fuentes ni trazas
viejas:

```python
screen_angle: int = 0             # 0 | 90 | 180 | 270, screen.orientation.angle
linear_accel: tuple[float, float, float] = (0.0, 0.0, 0.0)  # m/s² sin gravedad
```

`accel`, `gyro` y `orientation` conservan su semántica actual (frame del
dispositivo, orientación relativa al neutro). Maldito Pino no cambia.

El `state` de la PWA suma campos **opcionales**; el servidor tolera que falten y
`protocol` sigue en `2`:

| Campo | Tipo | Uso |
| --- | --- | --- |
| `screen` | `0/90/180/270` | normalizar ejes a la pantalla (`ControllerFrame.screen_angle`) |
| `linear` | `[x, y, z]` m/s² | aceleración sin gravedad |
| `aim_sensitivity` | `0.4..2.5` | preferencia del jugador |

Si `linear` falta, el servidor lo deriva de `accel` con un pasabajos de gravedad
(τ = 0,5 s): `g ← exp(-dt/τ)·g + (1-exp(-dt/τ))·a`, `linear = a - g`. La
derivación es determinista y testeable con trazas.

## Ejes y pantalla

`beta`/`gamma` y `gyro` son del dispositivo. El mismo movimiento cambia de eje
cuando el teléfono gira. Antes de reconocer, el vector se rota al frame de
pantalla:

| `screen` | `x_pantalla` | `y_pantalla` |
| --- | --- | --- |
| 0 | `x` | `y` |
| 90 | `-y` | `x` |
| 180 | `-x` | `-y` |
| 270 | `y` | `-x` |

Se aplica a `(gyro[1], gyro[2])` para tasas y a `(gamma, beta)` para posturas;
`gyro[0]` (α, normal a la pantalla) no rota. Canales resultantes:

- `pitch_rate`: rotación sobre el eje horizontal de la pantalla (mirar arriba/abajo).
- `yaw_rate`: rotación sobre el eje vertical de la pantalla (mirar izquierda/derecha).
- `roll_rate`: rotación sobre la normal de la pantalla (giro de muñeca).

La convención de signo se fija con dos tests de hardware, no con la tabla:

1. Con el teléfono en vertical y en horizontal, moverlo hacia la derecha física
   aumenta `aim_x`.
2. Con la pantalla vertical, mover el teléfono hacia arriba mueve el puntero
   hacia arriba (en coordenadas DOM, `aim_y` disminuye). El test congela la
   convención elegida.

## Catálogo v1

Todos los gestos se reconocen siempre y son deterministas; el manifest decide
cuáles se entregan y cuáles se muestran. Los parámetros viven en un solo módulo
`toxinator/input/gestures/config.py`.

| Gesto | Tipo | Salida | Direcciones |
| --- | --- | --- | --- |
| `tilt` | postura | `axes["tilt_x"]`, `axes["tilt_y"]` | — |
| `steer` | postura | `axes["steer"]` | — |
| `aim` | postura + puntero | `axes["aim_x"]`, `axes["aim_y"]`, `pointer` | — |
| `flick` | evento | `Gesture` | `up`, `down`, `left`, `right` |
| `swing` | evento | `Gesture` | `up`, `down`, `left`, `right` |
| `twist` | evento | `Gesture` | `cw`, `ccw` |
| `shake` | evento | `Gesture` | — |
| `flip` | evento | `Gesture` | `up`, `down` |

### Constantes iniciales

| Constante | Valor | Uso |
| --- | --- | --- |
| `TILT_DEADZONE` | 3° | ignora temblor de mano |
| `TILT_SATURATION` | 30° | postura a fondo de escala |
| `TILT_SMOOTH_TAU` | 60 ms | EMA de postura |
| `STEER_SATURATION` | 25° | volante a tope |
| `STEER_EXPO` | 1.4 | curva de dirección |
| `FLICK_START` | 11,8 m/s² (1,2 g) | pico que abre el evento |
| `FLICK_RELEASE` | 3,4 m/s² (0,35 g) | pico anterior que habilita |
| `FLICK_WINDOW` | 150 ms | ventana de pico |
| `FLICK_MAX` | 34,4 m/s² (3,5 g) | intensidad 1.0 |
| `FLICK_AMBIGUITY` | 0,70 | eje secundario / principal |
| `FLICK_COOLDOWN` | 300 ms | anti-rebote |
| `SWING_START` | 180 °/s | abre el arco |
| `SWING_END` | 90 °/s | cierra el arco |
| `SWING_MIN` | 80 ms | duración mínima |
| `SWING_INTENSITY` | 360° | ángulo para intensidad 1.0 |
| `SWING_COOLDOWN` | 400 ms | anti-rebote |
| `TWIST_START` | 60 °/s | abre el giro |
| `TWIST_ANGLE` | 40° | ángulo mínimo |
| `TWIST_WINDOW` | 500 ms | ventana del giro |
| `TWIST_INTENSITY` | 120° | ángulo para intensidad 1.0 |
| `TWIST_COOLDOWN` | 300 ms | anti-rebote |
| `SHAKE_RATE` | 120 °/s | excursión válida |
| `SHAKE_REVERSALS` | 3 | cambios de signo |
| `SHAKE_WINDOW` | 700 ms | ventana |
| `SHAKE_COOLDOWN` | 800 ms | anti-rebote |
| `FLIP_ANGLE` | 140° | giro acumulado |
| `FLIP_WINDOW` | 600 ms | ventana |
| `FLIP_INTENSITY` | 180° | ángulo para intensidad 1.0 |
| `FLIP_COOLDOWN` | 800 ms | anti-rebote |
| `AIM_DEADZONE` | 6 °/s | deriva y temblor |
| `AIM_FOV` | 60° | grados para cruzar la pantalla |
| `AIM_SENSITIVITY` | 1.0 (0.4–2.5) | preferencia |
| `BUFFER_SECONDS` | 0.5 s | historia del reconocedor |
| `EVENT_QUEUE` | 32 | eventos pendientes por slot |

### `tilt`

`tilt_x = clamp(deadzone(gamma_pantalla, 3°) / 30°, -1, 1)` con signo positivo a
la derecha; `tilt_y` análogo con `beta_pantalla` y positivo arriba. La deadzone y
el corte de 0,4° se aplican en grados sobre el valor filtrado, antes de
normalizar, para que el reposo no vibre. Se suaviza con EMA de 60 ms. Sin
calibración no hay postura: el neutro es la pose del último `calibrate`.

### `steer`

`steer = signo(tilt_x)·min(1, |tilt_x|·30°/25°)^1.4`. Separado de `tilt` porque
un volante necesita saturación temprana y curva; los juegos de puntería siguen
usando `tilt` lineal.

### `flick`

Se dispara con aceleración **lineal**; el eje dominante define la dirección.

```text
si |linear| < FLICK_RELEASE: habilitado = True
si habilitado y |linear| >= FLICK_START:
    abrir ventana de 150 ms, recordar pico y vector en el pico
    habilitado = False
al cerrar la ventana:
    eje = componente dominante del vector del pico (pantalla)
    si |secundario| / |principal| > 0.70: descartar (ambiguo)
    si pico < FLICK_START: descartar
    emitir flick(dirección=signo(eje), intensidad=clamp((pico-11.8)/22.6))
```

No confundir con una caída libre: `|linear|` cerca de 0 no dispara. El cooldown
de 300 ms impide que un rebote mecánico emita dos eventos.

### `swing`

Integra el ángulo recorrido mientras `|gyro_pantalla| > SWING_START`. Al bajar
de `SWING_END` con al menos 80 ms de arco, emite `swing` con la dirección del eje
dominante en el pico e intensidad `min(1, ángulo/360°)`. Es el gesto de bolos y
tenis: importa el arco, no el pico instantáneo.

### `twist`

Acumula `roll_rate` con signo. Cuando `|roll_rate| > 60 °/s` abre la ventana; si
el acumulado llega a 40° antes de 500 ms, emite `twist` `cw`/`ccw` con
intensidad `min(1, |ángulo|/120°)`. Un giro de muñeca para recargar o cambiar de
arma. Se cancela si `|tilt|` supera 35° durante la ventana, para no confundirlo con
`flip`.

### `shake`

Cuenta reversiones del eje dominante de `gyro_pantalla` donde cada excursión
supera 120 °/s. Tres reversiones en 700 ms emiten `shake` con intensidad
`min(1, reversiones/6)`. Cooldown 800 ms. Es el gesto de "sacudir para
zafarse".

### `flip`

Como `twist`, pero exige que el signo de la gravedad sobre la normal de la
pantalla cambie (cara arriba ↔ cara abajo) y que el ángulo acumulado llegue a
140° en 600 ms. La dirección es `up` al pasar a cara arriba y `down` al pasar a
cara abajo. Es deliberadamente difícil de disparar por accidente.

## Aim (air mouse)

Puntero relativo sin barra IR: integra la tasa angular de la pantalla y la mueve
en coordenadas normalizadas.

```text
dt = clamp(t - anterior, 0, 0.05)
w_yaw   = deadzone(yaw_rate, 6°/s)
w_pitch = deadzone(pitch_rate, 6°/s)
aim_x += (w_yaw   / 60°) · dt · sensibilidad
aim_y -= (w_pitch / 60°) · dt · sensibilidad
aim_x, aim_y = clamp(0, 1)
```

Reglas:

- Arranca en `(0.5, 0.5)` y el juego lo recibe en `axes["aim_x"]`/`["aim_y"]`.
- Si el juego declara `aim` y **no hay touch activo**, el hub pone
  `frame.pointer = (aim_x, aim_y)`. Si hay touch o mouse apretado, gana el touch:
  el jugador puede alternar sin cambiar de modo.
- `aim_sensitivity` viene del celular (ajustes) y se clampea a `0.4..2.5`.
- No usa magnetómetro ni `alpha`: no hay yaw absoluto, solo integración. La
  deadzone de 6 °/s absorbe el sesgo estático del giroscopio.
- La deriva se corrige con recentrar; no hay retorno automático al centro, porque
  pelea con el jugador.
- En el simulador, el mouse ya es `pointer` absoluto y `aim` no lo pisa.

## Calibración y recentrar

`calibrate` (cliente → servidor) pasa a ser **recenter** completo:

1. `neutral = raw_orientation` del slot.
2. `aim = (0.5, 0.5)`.
3. Se vacían buffers, ventanas y cooldowns del reconocedor.
4. Se responde `calibrated` y la PWA muestra el aviso.

Desde el juego: `ctx.phone.recenter(slot=None)` hace lo mismo del lado del
servidor y emite `calibrated` para el feedback; no hace round-trip por el
cliente. Desde el celular: si el perfil declara `aim`, la PWA muestra un chip
**CENTRAR** en la zona táctil que manda `calibrate`.

Sin calibración inicial, `tilt` y `steer` no se emiten; `aim` arranca centrado
y los eventos funcionan, porque no dependen del neutro.

## Manifest y perfil

```toml
[controller]
gestures = ["tilt", "aim", "flick"]
hint = "Apuntá y sacudí para tirar"

[controller.gesture_labels]
tilt = "Inclinar"
aim = "Apuntar"
flick = "Sacudir"
```

- `gestures`: nombres canónicos, máximo 8. Un nombre desconocido se ignora con
  warning; el resto del manifest se carga igual.
- `[controller.gesture_labels]`: label visible ≤ 24 caracteres por gesto
  declarado. Sin label se usa un texto por defecto del catálogo.
- Los gestos declarados son el contrato: el hub filtra los eventos a ese
  conjunto. Declarar de menos es un bug visible, no silencioso, porque la banda
  de la PWA no muestra el gesto.
- El perfil WebSocket suma:

```json
{
  "gestures": [
    { "name": "tilt", "label": "Inclinar", "kind": "posture" },
    { "name": "aim", "label": "Apuntar", "kind": "pointer" },
    { "name": "flick", "label": "Sacudir", "kind": "event" }
  ]
}
```

La PWA muestra una **banda de gestos** sobre la zona táctil con label e ícono
por gesto, y el chip de recentrar si hay `aim`. No hay tutorial animado en v1.

## Uso desde un juego

El juego no registra nada en runtime: declara en el manifest y lee el estado.

```python
state = self.ctx.input_state
slot = state.primary_slot()
frame = state.primary_frame()
if frame is not None:
    aim_x = frame.axis("aim_x")          # postura
    aim_y = frame.axis("aim_y")
    tilt = frame.axis("tilt_x")
    if frame.pointer is not None:        # touch, mouse o aim
        ...

if slot is not None:
    for gesture in state.gestures_for(slot):
        if gesture.name == "flick":
            self.launch(direction=gesture.direction, power=gesture.intensity)
```

- `gestures_for(slot)` devuelve solo los eventos de ese jugador, ya filtrados
  por lo declarado.
- Los eventos no se repiten en el frame siguiente: si el juego no los procesa
  en ese `update`, se pierden. Es a propósito, para que un `flick` no dispare dos
  veces.
- `frame.pointer` sigue siendo la vía recomendada para apuntar: el juego no
  necesita saber si viene de touch, mouse o `aim`.
- Los juegos con gestos deben ofrecer un camino alternativo por botón o stick
  (los gestos son best-effort: sin sensores no existen).

## Simulador de teclado/mouse

`KeyboardMouseSource` no corre el reconocedor: emite los mismos `Gesture`
desde teclas canónicas, con intensidad fija `0.8`:

| Tecla | Gesto | Dirección |
| --- | --- | --- |
| `F` | `flick` | `up` |
| `G` | `swing` | `right` |
| `T` | `twist` | `cw` |
| `H` | `shake` | — |
| `V` | `flip` | `down` |
| mouse | `aim` / `pointer` | absoluto |

Un juego que declara un gesto se puede jugar entero con teclado/mouse: la tecla
reemplaza la intención y el mouse apunta. `KeyboardMouseSource` suma
`gestures: true` a sus capacidades. No hay tecla de recentrar en el simulador:
el mouse ya es un puntero absoluto y no tiene drift que corregir.

## Métricas y criterios de aceptación

Unitarios:

- Cada gesto contra ondas sintéticas (seno, rampa, pulso) y contra su versión
  espejada: misma intensidad, dirección opuesta.
- Ambigüedad de `flick`: vector a 45° descartado; a 20° del eje, aceptado.
- `screen_angle` 0/90/180/270: el mismo gesto produce la misma dirección
  relativa a la pantalla.
- Cooldowns: dos pulsos juntos producen un evento, no dos.
- `aim`: deadzone no mueve; sensibilidad 0.5 tarda el doble; recentrar vuelve a
  0.5; touch gana sobre `aim`.
- Hub: un evento sobrevive a un frame pisado; filtro por gestos declarados;
  cola acotada; limpieza al desconectar.
- Manifest: nombres inválidos, labels largos, `gestures` no lista.

Trazas:

- `tests/fixtures/traces/gestures/*.jsonl` con frames normalizados y un sidecar
  `*.expected.json` con los eventos esperados (`t`, `name`, `direction`,
  `intensity` en buckets de 0.25). El formato de traza no cambia; `screen_angle` y
  `linear_accel` son campos opcionales.
- Mínimo por gesto: 5 grabaciones reales de 3 teléfonos distintos si hay
  hardware; si no, sintéticas equivalentes.
- Negativos obligatorios: teléfono en la mesa 10 min, caminando 5 min, pasando
  de mano 2 min, escribiendo con el teléfono apoyado 2 min.

Criterios:

- `flick`, `swing`, `twist`, `shake` y `flip`: ≥ 90% de detección sobre las
  grabaciones etiquetadas.
- Cero falsos positivos en la suite negativa.
- Latencia: el evento sale a ≤ 3 frames del pico etiquetado.
- `aim`: deriva ≤ 0,10 de pantalla en 30 s con el teléfono quieto.
- Maldito Pino se comporta igual que hoy (test de regresión con la misma traza).

Manual (checklist): cada gesto en vertical y horizontal, con el teléfono en la
mano y con carcasa; recentrar desde el juego y desde el chip; sensores apagados
sin crash.

## Laboratorio

`toxinator dev gestures` (o `toxinator dev phone --gestures`):

- Muestra por slot: crudo vs. filtrado de `accel`, `linear`, `gyro`, posturas,
  `aim` y los eventos con confianza.
- `--record <ruta>` graba traza normalizada + sidecar de eventos.
- `--replay <ruta>` reproduce una traza sin teléfono, con `--loop` y `--speed`.
- `--trace` imprime una línea por evento con `t`, nombre, dirección e intensidad.

Es el banco de tuning: los umbrales se ajustan contra un teléfono real y contra
las trazas, no "a ojo" en el juego.

## API y migración

- `API_VERSION` `0.3` → `0.4`; `requires_api` sin cambios de sintaxis.
- `toxinator.api.input` suma `Gesture`, `ControllerFrame.screen_angle`,
  `ControllerFrame.linear_accel`, `InputState.gestures` y helpers
  `gestures_for(slot)` / `gesture(name)`.
- `toxinator.api.phone.PhoneService` suma `recenter(slot=None)`.
- `ControllerInfo.capabilities` suma `gestures`.
- Alias `A`/`B`: se mantienen en `0.4` y se retiran en `0.5` (ver ADR-0010).
- `KeyboardMouseSource`: teclas nuevas, capacidades y gestos sintéticos.
- PWA: campos opcionales del `state`, banda de gestos, chip de recentrar y
  sensibilidad en ajustes.
- Maldito Pino no se toca en el milestone 1. En el milestone 4 migra
  `_power_level`/`_spin_from` a `tilt` y `swing` con paridad de tests, como
  prueba de que el catálogo cubre un juego real.

## Milestones

1. **Núcleo**: `Gesture` en la API, `screen_angle`/`linear_accel`, reconocedor con
   `tilt`/`flick`/`swing`, cola de eventos en el hub, tests sintéticos y
   `input_state.gestures`.
2. **Completo**: `aim`, `twist`, `shake`, `flip`, recentrar, simulador, manifest
   y perfil, banda de gestos en la PWA.
3. **Laboratorio**: `toxinator dev gestures`, grabación/replay, trazas reales y
   suite negativa.
4. **Migración**: Maldito Pino a `tilt` + `swing` con regresión, checklist manual.

## Riesgos

- **Submuestreo**: los sensores disparan a 60–200 Hz y la PWA envía a 60 Hz; un
  pico puede caer entre muestras. Se mitiga con ventanas de 150–700 ms y
  exigiendo dos muestras; si no alcanza, se agrega un `peaks` opcional al
  payload.
- **Variación entre teléfonos**: sesgo de giroscopio, carcasa y forma de agarrar.
  Por eso los umbrales son conservadores, hay sensibilidad por jugador y el
  laboratorio es parte del milestone.
- **Accesibilidad**: un gesto puede ser imposible para algún jugador. Todo juego
  que declare gestos debe ofrecer un camino por botón o stick; se documenta en la
  skill de desarrollo, no se impone en el manifest.
- **Sensores apagados**: sin HTTPS o sin permiso no hay gestos. La PWA lo avisa y
  el juego debe seguir jugable.
- **Falsos positivos por conversación**: hablar con el teléfono en la mano mueve
  el giroscopio. `shake` y `twist` son los más expuestos; los cooldowns y la
  ventana corta los contienen.
- **Filtro por manifest**: si un juego declara mal un nombre, el gesto no llega.
  Se compensa con el warning al cargar y con el laboratorio, que muestra el
  conjunto activo.
