# Mando v2: anatomía, perfil por juego y protocolo

Spec de implementación del mando celular v2. Las decisiones están en
[ADR-0007](../adr/0007-phone-controller-v2.md) y el avatar en
[ADR-0008](../adr/0008-avatar-from-photo.md). Este documento fija el contrato que
comparten la PWA, el servidor, la API y los juegos.

> **Estado**: milestone 1 implementado (PWA v2, protocolo v2, teclado/mouse,
> panel y foto). El editor de avatares es milestone 2.

## Alcance

Entra en la v1:

- PWA nueva con botones × ○ □ △, `options`, `L1`/`R1`, stick izquierdo y zona
  táctil derecha.
- Layouts landscape y vertical, automáticos, con override por juego y candado
  manual.
- Perfil `controller` extendido: orientación, labels, botones visibles, panel de
  imagen estática y bandera de cámara.
- Captura de foto por HTTP autenticado.
- `KeyboardMouseSource` en el `InputHub` para manejar la consola y jugar sin
  celular.
- Migración de launcher y Maldito Pino, limpieza de Wiimote.

No entra: d-pad, L2/R2, minimapa vivo, micrófono, avatares (milestone 2).

## Anatomía del mando

La PWA tiene dos layouts con paridad funcional; no hay botones exclusivos de uno.

```text
LANDSCAPE                                  VERTICAL
┌────────────────────────────────────┐    ┌──────────────┐
│ P1 · JUEGO            [PANEL]      │    │ P1 · JUEGO   │
│                                    │    │  [PANEL]     │
│      ╭────────────╮                │    │              │
│      │  zona      │      △         │    │     △        │
│      │  táctil    │   □  ○         │    │  □     ○     │
│      │  derecha   │      ×         │    │     ×        │
│      ╰────────────╯   options      │    │  options     │
│  ╭──╮                              │    │ ╭──────────╮ │
│  │◉ │  stick izquierdo    L1  R1   │    │ │  zona    │ │
│  ╰──╯                              │    │ │  táctil  │ │
│                                    │    │ ╰──────────╯ │
│  [CÁMARA]                 [≡]      │    │ ╭──╮         │
└────────────────────────────────────┘    │ │◉ │ L1  R1  │
                                          │ ╰──╯         │
                                          └──────────────┘
```

Reglas:

- El stick izquierdo se arrastra desde el centro y vuelve al soltar; el pulgar
  no necesita levantarse para repetir.
- La zona táctil derecha es absoluta: la posición del dedo es la posición
  apuntada (0..1 en ambos ejes).
- `options` va arriba de los botones de acción, fuera del alcance accidental del
  pulgar.
- `L1`/`R1` van en el borde superior, alcanzables con los índices.
- El panel de juego, cuando existe, ocupa el espacio libre superior y se puede
  expandir tocándolo.
- El botón de cámara solo aparece si el perfil declara `camera = true`.
- En modo launcher se muestran los cuatro botones de acción, stick y un hint; el
  panel y la cámara se ocultan.
- Área segura: `env(safe-area-inset-*)` en los cuatro bordes; nada de texto
  crítico bajo el notch.
- Sin scroll de página; `touch-action: none` en las zonas de juego.

## Botones canónicos

| Canónico   | Glifo | Alias | Teclado | Mouse       |
| ---------- | ----- | ----- | ------- | ----------- |
| `cross`    | ×     | `A`   | Enter, J| clic izq.   |
| `circle`   | ○     | `B`   | Esc, K  | clic der.   |
| `square`   | □     | —     | L       | —           |
| `triangle` | △     | —     | I       | —           |
| `options`  | ≡     | —     | Tab     | —           |
| `l1`       | L1    | —     | Q       | —           |
| `r1`       | R1    | —     | E       | —           |

- El frame emite el nombre canónico y, si corresponde, el alias: apretar ×
  produce `{"cross", "A"}`; apretar ○ produce `{"circle", "B"}`.
- Los alias `A`/`B` se retiran en API `0.4`.
- El launcher usa `cross` para activar y `circle` para volver.
- `options` lo consume el juego; la consola no lo intercepta.
- Los labels visibles salen de `profile.labels`; si faltan, se usan `Acción`,
  `Volver`, `Pausa` para `options` y vacío para el resto.

## Ejes, stick y touch

`ControllerFrame` gana dos ejes nuevos:

| Eje       | Rango  | Origen                                  |
| --------- | ------ | --------------------------------------- |
| `move_x`  | -1..1  | stick izquierdo                         |
| `move_y`  | -1..1  | stick izquierdo (positivo = arriba)     |
| `touch_x` | 0..1   | zona táctil derecha / dedo / mouse      |
| `touch_y` | 0..1   | zona táctil derecha / dedo / mouse      |
| `pointer` | 0..1×2 | primer touch activo o posición del mouse|

Reglas:

- Deadzone radial de `0.18`; magnitud recortada a un círculo unitario.
- El stick vuelve a `(0, 0)` al soltar y en `resetInputs()`.
- `pointer` se llena con el primer touch (comportamiento actual) y con el mouse.
  Los juegos deben usar `frame.pointer` para apuntar, no `touch[0]`.
- En launcher, el stick y el puntero navegan; un puntero quieto en el centro no
  repite. La repetición por dirección se mantiene como hoy (0.35 s + 0.12 s).

## Orientación

- `profile.orientation` es `auto` (default), `portrait` o `landscape`.
- La PWA detecta el layout con `matchMedia("(orientation: portrait)")` y lo
  expone en `body[data-orientation]`; no rota el contenido 90°.
- Si el juego exige una orientación y el teléfono está en la otra, se muestra un
  aviso "Girá el teléfono" y se mantiene el layout exigido usando el alto/ancho
  reales; los controles no se desincronizan.
- El candado manual fija el layout actual hasta que se toca de nuevo; se guarda
  en `localStorage` y no viaja al servidor.
- Cambiar de orientación no corta la conexión ni resetea botones.

## Perfil por juego

El manifest `[controller]` se extiende; los valores fuera de rango se clampean y
caen al default sin romper la carga.

```toml
[controller]
layout = "default"        # default | motion | touch (énfasis, no anatomía)
skin = "toxinator"        # skin engine se mantiene; v1 solo trae "toxinator"
orientation = "auto"      # auto | portrait | landscape
hint = "Mantené × para cargar"   # ≤ 80
camera = false
gestures = ["tilt", "flick"]     # ver docs/design/gestures.md

[controller.labels]
cross = "Tirar"           # ≤ 24
circle = "Volver"
square = ""
triangle = ""
options = ""
l1 = ""
r1 = ""

[controller.gesture_labels]     # opcional: labels de la banda de gestos
tilt = "Inclinar"
flick = "Sacudir"

[controller.panel]        # opcional
title = "Mapa"            # ≤ 40
image = "assets/mapa.png" # relativo a los assets del juego
fit = "contain"           # contain | cover | stretch
```

- `layout` conserva los valores viejos para no romper manifiestos existentes,
  pero solo cambia el hint y el énfasis visual del panel.
- `skin` mantiene el motor; las skins tokyo se retiran del CSS y quedan como deuda
  si alguien las pide.
- `camera = true` muestra el botón de captura; sin HTTPS el mando avisa que hace
  falta HTTPS al tocarlo.
- Un juego externo con `[controller]` incompleto sigue funcionando con los
  defaults.
- El perfil que viaja por WebSocket agrega `buttons` (qué controles mostrar) y
  `panel`; el servidor resuelve `panel.image` a una `url` bajo
  `/game-assets/<game-id>/`.
- `gestures` declara los gestos de plataforma que el juego consume; viaja en el
  perfil como `[{name, label, kind}]` y la PWA muestra la banda de gestos. El
  contrato completo está en [gestures.md](gestures.md).

## Protocolo WebSocket v2

`protocol = 2`. El servidor rechaza un `hello` con otra versión con
`{"type": "error", "code": "bad-protocol"}` y cierra.

Cliente → servidor:

| Tipo        | Payload                                                        |
| ----------- | -------------------------------------------------------------- |
| `hello`     | `token`, `name`, `protocol: 2`                                 |
| `state`     | `t`, `buttons`, `move`, `touch`, `orientation`, `accel`, `gyro`|
| `calibrate` | —                                                              |
| `ping`      | `t`                                                            |

`state` a 60 Hz:

```json
{
  "type": "state",
  "t": 12.5,
  "buttons": ["cross", "l1"],
  "move": [0.3, -0.8],
  "touch": [{ "id": 0, "x": 0.4, "y": 0.6, "pressure": 1 }],
  "orientation": [10.0, 20.0, 30.0],
  "accel": [0.0, 0.0, 9.8],
  "gyro": [0.0, 0.0, 0.0]
}
```

Servidor → cliente:

| Tipo         | Payload                                              |
| ------------ | ---------------------------------------------------- |
| `welcome`    | `protocol`, `slot`, `controller_id`                  |
| `mode`       | `mode` (`launcher`/`game`)                           |
| `controller` | `profile` (sección anterior) o `null`                |
| `panel`      | `panel` (`{title, url, fit}`) o `null`               |
| `haptic`     | `pattern` (ms on/off, ≤ 12 valores)                  |
| `audio`      | `action`, `frequency`, `duration`, `volume`          |
| `calibrated` | —                                                    |
| `pong`       | `t`                                                  |
| `error`      | `code`                                               |

Compatibilidad: `buttons` acepta cualquier string; un botón desconocido se
ignora en la UI y se reenvía igual. `touch` mantiene el shape actual. Un cliente
viejo no existe en la práctica porque el servidor sirve la PWA.

## Panel de juego

- Solo imagen estática en v1 (jpg/png/webp, ≤ 4 MB).
- `GET /game-assets/<game-id>/<ruta>` sirve únicamente archivos dentro de los
  assets del juego activo; se prohíbe `..`, symlinks fuera del árbol y
  content-types desconocidos.
- El perfil manda la ruta; la PWA la muestra en el panel y permite expandirla.
- API runtime para cambiarlo en partida:

```python
ctx.phone.panel(title="Mapa", image="assets/mapa.png", fit="contain")
ctx.phone.clear_panel()
```

- `panel()` y `clear_panel()` son no-op sin celular conectado.
- El panel no captura input: los controles siguen vivos debajo.

## Foto

- `POST /api/photo?slot=N` con `X-Toxinator-Token: <token>` y
  `Content-Type: image/jpeg` (también `image/png`).
- Cuerpo 16 KB..2 MB; se rechaza con `413` fuera de rango y `415` si el tipo no
  es imagen.
- Respuesta `201 {"id": "...", "bytes": 123456}`.
- La consola guarda la foto en memoria durante la sesión y la entrega al flujo
  que la pidió (`DevServer.last_photo(slot)`); sin pedido explícito, se descarta
  al terminar la sesión.
- Requiere HTTPS en el teléfono; sobre HTTP el botón de cámara se muestra
  deshabilitado.
- En milestone 1 solo existe la captura y el endpoint; el editor de avatares de
  milestone 2 la consume.

## Teclado y mouse

`KeyboardMouseSource` implementa `ControllerSource`:

- `name = "keyboard"`, `ControllerInfo.source = "sim"`,
  `display_name = "Teclado"`, capacidades `buttons`, `axes`, `pointer`, `touch`.
- Slot por defecto `4` (fuera de los cuatro teléfonos), configurable con
  `--keyboard-slot`. No ocupa un chip de teléfono; el launcher muestra un
  indicador `TECLADO` cuando es el mando principal.
- Habilitado por defecto en `toxinator` y `toxinator play`; `--no-keyboard` lo
  apaga. En CI/headless queda apagado salvo pedido explícito.
- Mouse: la posición en la ventana se mapea a `pointer` 0..1; mientras hay un
  botón apretado se sintetiza un touch de un punto. Clic izquierdo = `cross`,
  derecho = `circle`.
- El launcher deja de registrar `arrow_*`, `enter` y `escape` por Panda3D y
  consume el frame del hub; conserva `d`/`s`/`c` como atajos de overlays.
- `InputState.primary_frame()` devuelve el primer frame vivo con
  `source="phone"` (menor slot); si no hay, el primer frame vivo de cualquier
  fuente. Launcher y juegos de un jugador lo usan.

## Migración

- `API_VERSION` `0.2` → `0.3`.
- `ControllerFrame` gana `move_x`/`move_y`; los alias `A`/`B` se emiten junto a
  `cross`/`circle`.
- Launcher: navegación por hub; `cross` activa, `circle` vuelve, stick/puntero
  mueven el foco.
- Maldito Pino: `primary_frame()`, `frame.pointer` para apuntar y `cross` para
  cargar/tirar.
- `DemoSource` sigue con `source="sim"` y botón `cross`.
- README, `GLOSSARY.md`, `docs/testing/manual-checklist.md`, `pyproject.toml` y
  ADR-0001 dejan de presentar Wiimote como pendiente.
- Tests de shell de la PWA se reescriben con los ids nuevos.

## Tests y criterios de aceptación

Unitarios:

- Protocolo: nombres canónicos, alias, `move` → ejes, touch/pointer, límites.
- Perfil: enums inválidos, clamps de labels/hint/title, panel inválido, `camera`.
- Teclado: mapa de teclas, mouse, slot, `primary_frame()` prefiere teléfono.
- Servidor: auth y límites de foto, `bad-protocol`, ruta de assets sin traversal.
- PWA: ids nuevos, `data-orientation`, glifos, ausencia de skins tokyo.

Manual (checklist):

- Android Chrome landscape y vertical; iOS Safari vertical.
- Cuatro botones + options + L1/R1, stick con retorno, touch absoluto.
- Vibración y tonos siguen funcionando; calibrar y sensores.
- Launcher completo sin celular usando solo teclado y mouse.
- Juego con perfil: labels, orientación forzada, panel y cámara.
- Foto sube por HTTPS y falla limpio por HTTP.

Criterio de aceptación: un juego existente (Maldito Pino) se juega igual que hoy
con celular, y se puede jugar de punta a punta con teclado/mouse.

## Milestones

1. **Mando v2**: ADRs y spec, protocolo v2, servidor, PWA nueva, teclado/mouse,
   migración de launcher/Maldito Pino, tests y limpieza de docs.
2. **Avatares**: captura desde el launcher, heurísticas de foto, editor,
   almacenamiento por perfil, `ctx.avatar` y render en launcher/juegos.

## Riesgos

- Safari iOS: orientación, cámara y audio requieren gesto; el candado manual
  puede no coincidir con la rotación real.
- Sin ML, el parecido inicial va a ser grueso; el editor es la válvula.
- El mouse como puntero absoluto puede sentirse raro para apuntar; se ajusta con
  sensibilidad en el preset del simulador.
- Un juego externo que use `frame(0)` directo no ve el teclado; se documenta
  `primary_frame()` en la skill de desarrollo.
