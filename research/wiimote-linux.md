# Wii Remote original en Linux: pairing, HID y sensores

> Research del ticket [#2](https://github.com/skalanux/wiIAsports/issues/2).
> Fecha: 2026-11-16. Entorno verificado: Omarchy (Arch), kernel `7.2.15-1-omarchy`,
> BlueZ `5.87`, Python `3.14.8`, Panda3D `1.10.16`.
>
> **Alcance y honestidad:** esta investigación se hizo **sin un Wiimote físico conectado**
> a esta máquina. Todo lo que describe el comportamiento del kernel/BlueZ se verificó
> contra el código fuente de las versiones exactas (`v7.2.15` y BlueZ `5.87`) y contra
> documentación de primera fuente. Lo que depende del hardware real (tasa efectiva,
> latencia, pairing de la unidad concreta, revisión del mando) queda marcado como
> **pendiente de validación**. No se inventaron mediciones.

---

## TL;DR

**Ruta recomendada:** emparejar una sola vez con el **botón rojo de sync** (no con
`1+2`), dejar que **BlueZ 5.87** haga el pairing y la reconexión, y leer los sensores
desde **`hid-wiimote` + `evdev` con `python-evdev`**. Nada de `hidapi` para el gameplay
normal, nada de `xwiimote`/`cwiid`, y no usar el soporte evdev nativo de Panda3D para
el Wiimote.

- El driver `hid-wiimote` es parte del kernel (in-tree) y expone **botones,
  acelerómetro, cámara IR (hasta 4 puntos), MotionPlus, rumble, LEDs y batería**
  como dispositivos evdev/sysfs separados. Es la vía más madura y con menos código
  propio.
- **`1+2` no sirve como método principal**: no crea bond, no habilita reconexión
  automática y, con el default `ClassicBondedOnly=true` de BlueZ 5.87, la conexión
  HID sin bond se rechaza. Además el PIN que usa BlueZ para `1+2` no es el que espera
  el Wiimote. Usar el botón rojo.
- **`python-evdev` 2.0.0** funciona en Python 3.14 (verificado compilando desde sdist
  en este equipo), pero **no publica wheels**: hay que compilar. Es la dependencia
  más “pesada” de la ruta, no un problema en Linux de escritorio.
- **IR:** el driver usa modo *basic* de la cámara: hasta **4 puntos x/y** a 1024×768,
  sin tamaño/intensidad y con sensibilidad fija (nivel 3 de Wii). Con una barra DIY de
  **2 LEDs** ya hay pointing de 2 puntos; no hace falta una barra de 4 LEDs, y con el
  driver estándar no se puede pedir modo extendido/full.
- **Speaker: no soportado** por `hid-wiimote`. Rumble: sí, pero binario (on/off).
- **60 FPS:** leer evdev una vez por frame alcanza; la latencia real hay que medirla.
  El presupuesto teórico es ~10 ms de reporte + ≤16.7 ms de frame + transporte, pero
  no hay una medición de primera fuente para el Wiimote.
- **Efecto secundario de Panda3D:** `ShowBase` abre todos los nodos evdev legibles,
  incluido el IR, así que la cámara se enciende aunque el juego no la use (§8.3).
  Es un costo de batería, no un bloqueante.

**Ruta en 5 pasos:**

1. Emparejar una vez con red sync (`bluetoothctl`) y verificar `Bonded: yes`.
2. Confirmar que `hid-wiimote` bindeó y que aparecen los nodos
   `Nintendo Wii Remote` / `Accelerometer` / `IR` (y `Motion Plus` si hay).
3. Implementar un `WiimoteSource` con `python-evdev` que agrupe nodos por
   `HID_UNIQ` y drene eventos una vez por frame.
4. Normalizar a `ControllerFrame` (botones, accel, gyro, pointer, battery) e
   inyectarlo en el task de Panda3D con `sort=-100`.
5. Dejar IR y MotionPlus para después; el MVP puede usar tilt + botones y el
   pointer del celular.

---

## 1. Entorno verificado en este equipo

Comandos y resultados relevantes (verificación local, 2026-11-16):

```text
$ bluetoothctl --version
bluetoothctl: 5.87

$ uname -r
7.2.15-1-omarchy

$ python3 --version
Python 3.14.8

$ modinfo hid-wiimote
filename: .../kernel/drivers/hid/hid-wiimote.ko.zst
description: Driver for Nintendo Wii / Wii U peripherals
author: David Herrmann
depends: ff-memless
parm: dpad_as_analog:Use D-Pad as main analog input (bool)

$ modprobe --show-depends hid-wiimote
insmod .../ff-memless.ko.zst
insmod .../hid-wiimote.ko.zst
```

Configuración del kernel relevante (`/proc/config.gz`):

```text
CONFIG_HID_WIIMOTE=m
CONFIG_BT_HIDP=m
CONFIG_INPUT_FF_MEMLESS=m
CONFIG_HIDRAW=y
CONFIG_UHID=m
CONFIG_LEDS_CLASS=y
CONFIG_POWER_SUPPLY=y
```

BlueZ instalado:

```text
$ grep -a -o 'wii_pincb' /usr/lib/bluetooth/bluetoothd
wii_pincb

$ grep -a -o 'Rejected connection from !bonded device' /usr/lib/bluetooth/bluetoothd
Rejected connection from !bonded device
```

Es decir: el `bluetoothd` de 5.87 incluye el manejo de PIN de Wiimote dentro de
`autopair` y el chequeo de `ClassicBondedOnly`. El módulo `hid-wiimote` está
disponible pero no estaba cargado porque no había un Wiimote conectado.

---

## 2. Arquitectura recomendada

```text
Wiimote (Bluetooth Classic HID)
        │  L2CAP HIDP (PSM 0x11/0x13)
        ▼
BlueZ 5.87 (bluetoothd)
  ├─ autopair: PIN legacy del Wiimote
  ├─ input profile: acepta HIDP y crea UHID (default UserspaceHID=true)
  └─ D-Bus: pairing/reconnect opcional
        │  bus 0x05 (BLUETOOTH), vendor 0x057e, product 0x0306/0x0330
        ▼
kernel hid-wiimote
  ├─ /dev/input/eventN  "Nintendo Wii Remote"              (botones + D-pad)
  ├─ /dev/input/eventN  "Nintendo Wii Remote Accelerometer"
  ├─ /dev/input/eventN  "Nintendo Wii Remote IR"           (4 puntos)
  ├─ /dev/input/eventN  "Nintendo Wii Remote Motion Plus"  (si hay MP)
  ├─ /sys/class/leds/<hid>:blue:p0..p3
  ├─ /sys/class/power_supply/wiimote_battery_<MAC>/capacity
  └─ /sys/bus/hid/devices/<hid>/{devtype,extension}
        │
        ▼
python-evdev (poll no bloqueante, 1 vez por frame)
        │
        ▼
ControllerFrame normalizado  →  Panda3D (task sort=-100)
```

**Wayland:** la ruta no depende del display server. `evdev` está debajo de
Wayland/X11; no hace falta XWayland, libinput ni un protocolo de input del
compositor. La app lee `/dev/input/event*` directamente y no necesita que la
ventana tenga foco para recibir los eventos del Wiimote. Lo único a cuidar es
que el compositor (y Panda3D, §8.3) pueden abrir los mismos nodos; leer evdev no
es exclusivo salvo que se haga `EVIOCGRAB`.

**Por qué esta ruta y no otra:**

| Opción | Veredicto | Motivo |
|---|---|---|
| `hid-wiimote` + `evdev` | **Recomendada** | Driver in-tree, todos los sensores, FF, LEDs, batería; sin protocolo propio. |
| `hidapi`/`hidraw` directo | Solo avanzado | Permisos root por defecto; escribir output reports compite con el driver (rumble/LED/DRM). |
| `xwiimote` (C) | No | Sin binding Python; proyecto poco activo; agrega una capa sobre lo mismo. |
| `cwiid` | No | Driver userspace viejo (2017), evita `hid-wiimote`; sin mantenimiento. |
| `pybluez` | No | Último release 2019; no hace falta: BlueZ ya hace el pairing. |
| `wiiuse` (C) | No para esta stack | Implementa su propio HID; duplica al kernel y agrega dependencia C. |
| evdev nativo de Panda3D | No para el Wiimote | Timestamps a tiempo de frame, mapeo de ejes gamepad, IR incompleto, sin MAC. |

---

## 3. Emparejamiento y reconexión (BlueZ 5.87)

### 3.1 Botón rojo vs `1+2`

El comentario del plugin de BlueZ (hoy fusionado en `autopair`) es explícito
[R7]:

| | **Red sync** (tapa de batería) | **`1+2`** |
|---|---|---|
| ¿Crea bond? | Sí | **No** (modo temporal/guest) |
| PIN que espera el Wiimote | BD_ADDR del host, en orden reverso | BD_ADDR del propio Wiimote, reverso |
| ¿Reconexión automática? | Sí, si se abrió el servicio HID | **No** |
| Modelos `RVL-CNT-01-TR` (0x0330) | Recomendado | Puede apagarse si el HID se abre antes de autenticar |
| Uso recomendado | **Pairing permanente** | Guest/debug, o conectores viejos sin bond |

Fuente del comportamiento de PIN y de la reconexión de un solo botón: Wiibrew
[R19] (documentación comunitaria de reverse engineering; es la referencia que usa
el propio driver) y el comentario de BlueZ [R7]. BlueZ usa la dirección del
**adaptador local** como PIN para cualquier Wiimote, también en `1+2` [R7]; el
Wiimote en `1+2` espera la dirección **del Wiimote**. Por eso `pair` en `1+2`
suele fallar con `AuthenticationFailed` (reportes de campo en [R15]). La ruta
correcta para `1+2` es **no parear**: conectar sin bond y con
`ClassicBondedOnly=false`.

**Consecuencia práctica:** usar el botón rojo para el mando “de la casa”. `1+2`
solo si se quiere un invitado sin reconexión automática, y sabiendo que en los
modelos TR puede no funcionar.

### 3.2 Qué hace BlueZ 5.87 exactamente

1. **El plugin separado `wiimote` ya no existe.** Fue eliminado en enero de 2025
   [R13]; su lógica de PIN se movió a `plugins/autopair.c` en el commit
   `c281bc4608` [R12]. En 5.79 `autopair.c` todavía no tenía `wii_pincb`; en 5.80
   sí. Es decir, **5.80+** tiene el manejo correcto; **5.73–5.79** tenían el bug de
   orden de plugins que mandaba `0000` como PIN [R14].
2. **`wii_pincb`** reconoce vendor/product `057e:0306`, `057e:0330` (y el LEGO
   `054c:0306`) o los nombres `Nintendo RVL-CNT-01`, `-TR`, `-UC`, `RVL-WBC-01`,
   y devuelve los 6 bytes de la dirección del adaptador local [R7].
3. **`ClassicBondedOnly` default = `true`** [R8][R9]. El chequeo se aplica antes
   de crear la conexión HIDP/UHID: si el dispositivo no está bonded, BlueZ
   escribe `Rejected connection from !bonded device` y aborta [R8]. Por eso `1+2`
   (sin bond) no conecta con la configuración por defecto.
4. **`UserspaceHID` default = `true`** [R8][R9]: BlueZ crea un dispositivo UHID con
   `bus = BUS_BLUETOOTH`, vendor/product del SDP y `uniq = BD_ADDR del Wiimote`
   [R10]. El `hid-wiimote` matchea por bus/vendor/product y se bindea igual que
   con HIDP del kernel [R1]. Hay un log de campo de un dispositivo `0330`
   (Wii U Pro) bindeado como `wiimote` sobre UHID en [R34]; el caso `0306` no se
   pudo verificar con hardware en esta investigación.
5. **`input` profile tiene `auto_connect = true`** [R11]: cuando el mando ya está
   conectado, BlueZ conecta el perfil HID sin intervención. La reconexión de un
   solo botón la inicia el Wiimote [R19]; BlueZ la acepta porque el dispositivo
   está bonded (si `ClassicBondedOnly=true`) [R8].

### 3.3 Receta de pairing (una sola vez)

Con el Wiimote apagado y el adaptador encendido:

```bash
bluetoothctl
```

Dentro de `bluetoothctl`:

```text
power on
pairable on
agent NoInputNoOutput
default-agent
scan on
# Ahora: abrir la tapa de baterías y presionar el botón ROJO de sync.
# Esperar a ver: [NEW] Device XX:XX:XX:XX:XX:XX Nintendo RVL-CNT-01
scan off
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
info XX:XX:XX:XX:XX:XX
```

El `info` exitoso debe mostrar:

```text
Paired: yes
Bonded: yes
Trusted: yes
Connected: yes
LegacyPairing: yes
UUID: Human Interface Device (00001124-0000-1000-8000-00805f9b34fb)
```

Notas:

- El botón rojo deja al Wiimote discoverable **20 s**; hacer `pair` dentro de esa
  ventana [R19]. Si se pasa, volver a presionarlo.
- `pair` puede desconectar el mando; hacer `connect` inmediatamente después.
- Si el `pair` falla con `AuthenticationFailed`, **no** deshabilitar `autopair` en
  5.87: en 5.80+ `autopair` es el único lugar donde vive `wii_pincb`; deshabilitarlo
  quita el PIN correcto. Verificar la versión y reintentar con red sync.
- `trust` no es estrictamente necesario para una conexión entrante de un bonded,
  pero ayuda a la política de auto-conexión y a `bluetoothctl connect`.

### 3.4 `1+2` como fallback (solo si hace falta)

Si se quiere usar `1+2` (por ejemplo, un mando invitado), hay que relajar el
chequeo de bond:

```ini
# /etc/bluetooth/input.conf
[General]
ClassicBondedOnly=false
```

```bash
sudo systemctl restart bluetooth
```

Luego:

```text
scan on
# presionar 1+2
connect XX:XX:XX:XX:XX:XX
# NO hacer pair: el PIN de 1+2 no es el que manda BlueZ.
```

Limitaciones:

- Sin bond no hay reconexión de un solo botón: hay que repetir `1+2` + `connect`
  cada vez.
- En `RVL-CNT-01-TR` (0x0330), Wiibrew indica que el HID data channel debe abrirse
  **después** de la autenticación; si se abre antes, el mando se apaga [R19]. Por
  eso `1+2` es riesgoso en TR.
- `ClassicBondedOnly=false` permite conexiones HID de dispositivos no bonded;
  es una relajación de seguridad. Volver a `true` si no se usa el modo guest.

### 3.5 Reconexión

Con el pairing por red sync ya hecho:

1. El Wiimote guarda el host y, al presionar cualquier botón, inicia la conexión
   (single-press reconnect) [R19].
2. BlueZ acepta al dispositivo bonded; el `input` profile tiene
   `auto_connect=true` [R11].
3. El kernel crea de nuevo los nodos evdev; la app debe detectar el hotplug (ver
   §5.7), no asumir que los fds siguen vivos.

Si no reconecta solo:

```bash
bluetoothctl connect XX:XX:XX:XX:XX:XX
```

mientras se presiona un botón del Wiimote. Si el mando estaba previamente
emparejado a una Wii, puede intentar reconectar a esa consola primero; el Wiimote
prueba los hosts guardados en orden inverso al último bond [R19]. Como el PC es
el bond más reciente, debería preferirlo; si no, volver a hacer red sync.

### 3.6 Múltiples Wiimotes

- Aparear **de a uno**: todos se llaman `Nintendo RVL-CNT-01` y `bluetoothctl`
  no los distingue por nombre. Encender/parear uno, confirmar MAC, apagarlo, seguir
  con el siguiente.
- Cada Wiimote crea su propio HID device y sus propios nodos evdev. El `HID_UNIQ`
  del HID device es el MAC del mando; es la clave para mapear nodos → jugador
  (ver §4.1).
- LEDs de jugador: el driver expone 4 LEDs por mando en
  `/sys/class/leds/<hid>:blue:p0..p3` [R2]. En 7.2.15 el driver enciende LED1 por
  defecto; la asignación automática por ID de conexión llegó después (commit
  `890f45e`, 2026-10) [R1]. Para 2–4 jugadores, setear a mano un LED por mando.
- 4 mandos es un objetivo razonable; el límite práctico depende del adaptador y
  de la congestión 2.4 GHz. No hay una medición de 4 Wiimotes simultáneos en esta
  investigación.

### 3.7 D-Bus (opcional, para un wizard dentro del juego)

No hace falta D-Bus para jugar: alcanza con parear una vez desde el sistema y
leer evdev. Si se quiere un wizard de pairing/reconexión:

- `org.bluez.Adapter1.StartDiscovery()` / `StopDiscovery()` [R18].
- `org.bluez.Device1.Pair()`, `Connect()`, `Disconnect()`, propiedad `Trusted`
  [R17].
- El PIN del Wiimote lo resuelve `autopair` dentro de `bluetoothd`; un agente
  `NoInputNoOutput` alcanza. No intentar devolver el PIN binario desde un agente
  D-Bus: la API de agente devuelve strings y el PIN del Wiimote son 6 bytes
  binarios [R7][R19].
- `dbus-fast` 5.2.0 tiene wheels para cp314 [R37] y es una opción mantenida;
  `pydbus`/`dbus-python` no se evaluaron en profundidad.

Ejemplo mínimo (solo conectar un mando ya pareado):

```python
import asyncio
from dbus_fast.aio import MessageBus

async def connect(mac: str):
    bus = await MessageBus().connect()
    intro = await bus.introspect("org.bluez", f"/org/bluez/hci0/dev_{mac.replace(':', '_')}")
    obj = bus.get_proxy_object("org.bluez", f"/org/bluez/hci0/dev_{mac.replace(':', '_')}", intro)
    dev = obj.get_interface("org.bluez.Device1")
    await dev.call_connect()

asyncio.run(connect("AA:BB:CC:DD:EE:FF"))
```

(El path exacto depende de `hci0`; enumerar `org.bluez` si hay varios adaptadores.)

---

## 4. Exposición de datos: `hid-wiimote` + evdev

### 4.1 Árbol de dispositivos por Wiimote

El driver crea **varios input devices separados** por mando, todos con parent el
HID device [R1][R2]. Nombres exactos (constantes del driver):

| Nodo | Nombre evdev | Contenido | Cuándo aparece |
|---|---|---|---|
| Botones | `Nintendo Wii Remote` | `EV_KEY`: A, B, 1, 2, +, −, Home, D-pad | Tras la detección inicial |
| Acelerómetro | `Nintendo Wii Remote Accelerometer` | `ABS_RX/RY/RZ`, rango −500..500 | Tras la detección inicial |
| IR | `Nintendo Wii Remote IR` | `ABS_HAT0X..HAT3Y`, x 0..1023, y 0..767 | Tras la detección inicial; se activa al abrirlo |
| MotionPlus | `Nintendo Wii Remote Motion Plus` | `ABS_RX/RY/RZ`, rango declarado −16000..16000 | Cuando el driver detecta MP (hasta 4 s) |

**Identidad del mando (MAC):** el driver **no** setea `input->uniq` ni
`input->phys` en sus input devices; crea el `input_dev` con parent el HID device
pero no copia esos campos [R1]. Por eso `evdev.InputDevice.uniq` queda vacío. La
MAC se obtiene del **HID parent**:

```text
/sys/class/input/eventN/device/device/uevent
  HID_NAME=Nintendo RVL-CNT-01
  HID_PHYS=<MAC del adaptador host>
  HID_UNIQ=<MAC del Wiimote>
```

Ese layout se verificó con un dispositivo HID Bluetooth real (UHID) en este
equipo: `HID_UNIQ` contiene la MAC del periférico. En el path HIDP del kernel,
`hidp` también setea `hdev->uniq` con la dirección destino [R4]. Es la forma
robusta de agrupar los 3–4 nodos de un mismo mando y de distinguir varios
Wiimotes.

### 4.2 Botones

Mapeo exacto del driver [R2]:

| Botón físico | Código evdev | Comentario |
|---|---|---|
| D-pad izquierda/derecha/arriba/abajo | `KEY_LEFT`, `KEY_RIGHT`, `KEY_UP`, `KEY_DOWN` | No `ABS_HAT`; son teclas |
| `+` | `KEY_NEXT` | ¡No es `KEY_KPPLUS`! |
| `−` | `KEY_PREVIOUS` | ¡No es `KEY_KPMINUS`! |
| `1` / `2` | `BTN_1` / `BTN_2` | |
| `A` / `B` | `BTN_A` / `BTN_B` | |
| `Home` | `BTN_MODE` | |

Valores: `EV_KEY` con `value=1` al presionar y `0` al soltar. El driver emite un
`SYN_REPORT` por reporte.

### 4.3 Acelerómetro

- El driver decodifica los 3 valores de 10 bits y reporta
  `ABS_RX = x - 0x200`, ídem Y/Z [R2]. Es decir: **cero en 512**, rango declarado
  −500..500.
- **No aplica calibración de fábrica.** El EEPROM del Wiimote guarda los valores
  de 0 g y 1 g por eje [R19], pero `hid-wiimote` no los lee ni los expone. La app
  recibe cuentas crudas.
- El sensor es un ADXL330 de ±3 g (en la revisión original) [R19]; la escala
  exacta por eje depende de la unidad. Para tilt no hace falta convertir a g:
  normalizar el vector alcanza. Para “g” reales, calibrar empíricamente.
- El acelerómetro no da traslación: integra aceleración y deriva. Para un juego,
  usarlo para **tilt/lean**, no para posición.

### 4.4 MotionPlus

- Se detecta por polling cada **4 s** (`wiimote_init_poll_mp`) y se carga/descarga
  el módulo MP dinámicamente [R1]. Al conectar, puede tardar hasta 4 s en aparecer
  el nodo `Nintendo Wii Remote Motion Plus`.
- `devtype` ayuda: `gen20` = `RVL-CNT-01-TR` con MotionPlus **integrado**;
  `gen10` = original sin MP integrado (puede tener un dongle MotionPlus externo,
  que se detecta por polling) [R1].
- El driver normaliza las dos escalas del MP (slow/fast) a
  ~**167.564 unidades por °/s**, con cero en 0 [R2, comentario en
  `wiimod_mp_in_mp`]. El rango declarado es ±16000; una rotación rápida puede
  superar ese rango nominal, así que no confiar en `absinfo.max` para clampear.
- El driver **no** aplica calibración de fábrica del MP; hay que estimar el bias
  en reposo (promedio de ~1 s) y restarlo.
- El nodo MP solo recibe datos cuando la app lo abre: `wiimod_mp_open` setea
  `WIIPROTO_FLAG_MP_USED` y re-selecciona el DRM [R2].

### 4.5 Cámara IR

- La cámara es de **128×96** con procesamiento integrado; entrega hasta **4
  objetos**, con resolución subpíxel de **1024×768**, no imagen cruda [R19].
- `hid-wiimote` pide **modo basic** al abrir el nodo IR: `wiimod_ir_open` llama a
  `wiimod_ir_change(WIIPROTO_FLAG_IR_BASIC)` [R2]. Basic = 10 bytes = 4 puntos
  x/y (sin tamaño ni intensidad) [R19].
- Los 4 puntos se exponen como pares `ABS_HAT0X/Y`, `ABS_HAT1X/Y`,
  `ABS_HAT2X/Y`, `ABS_HAT3X/Y`, con x 0..1023 e y 0..767 [R2].
- **Slot vacío:** la cámara manda `0xFF` en los bytes del punto; el driver los
  decodifica como `(1023, 1023)`, porque los 10 bits quedan en 1. Ojo: el rango
  declarado de y es 0..767, pero `input_set_abs_params` no clampea el valor
  crudo, así que el sentinel de y es 1023 (fuera del rango nominal). Hay que
  filtrar `(1023, 1023)` [R19 + fórmula del driver R2]. Un punto real en la
  esquina exacta es indistinguible; es un caso límite aceptable.
- El orden de slots lo asigna la cámara, no está ordenado por x. Para una barra
  de 2 clusters, ordenar por x y emparejar izquierda/derecha.
- **No hay API para pedir modo extended/full** por evdev: el driver soporta
  internamente `IR_EXT`/`IR_FULL`, pero solo `wiimod_ir_open` llama a
  `IR_BASIC` [R2]. Para tamaño/intensidad/bbox habría que bypassear el driver
  (hidraw + protocolo propio), que no se recomienda para v1.
- La sensibilidad es fija: el driver escribe el bloque de sensibilidad
  `02 00 00 71 01 00 aa 00 64` + `63 03`, que es el **nivel 3 de Wii** en la
  tabla de Wiibrew [R2][R19]. No hay sysfs para cambiarla.
- La cámara consume bastante energía; el driver la mantiene apagada hasta que se
  abre el nodo IR, y la apaga al cerrarlo [R2]. Abrir el nodo IR todo el tiempo
  acorta la batería.

### 4.6 Rumble

- `wiimod_rumble_probe` registra `FF_RUMBLE` en el input device principal y usa
  `input_ff_create_memless` [R2].
- El Wiimote tiene **un solo motor**: el driver prende si `strong_magnitude` o
  `weak_magnitude` son distintos de cero, y apaga si ambos son cero [R2]. Es
  **binario**, no hay intensidad.
- Se controla por evdev FF (`EV_FF`), no por un report custom [R23]. Ver §9.3.

### 4.7 LEDs

- Cuatro LEDs de jugador por mando, clase LED:
  `/sys/class/leds/<dev_name>:blue:p0` … `p3`, `brightness` 0/1 [R2].
- `dev_name` es el nombre del HID device (ej. `0005:057E:0306.0003`), no la MAC.
  Para mapear LED → MAC, leer el `uevent` del HID parent.
- En 7.2.15 el driver enciende LED1 al probear [R2]; la asignación automática por
  ID de conexión es posterior (commit `890f45e`, 2026-10) [R1]. Si se usan 4
  mandos en 7.2.15, asignar LEDs a mano.
- **Permisos:** `brightness` es un atributo sysfs `root:root 0644` (verificado
  localmente); un usuario normal no puede escribirlo. Los LEDs no son necesarios
  para jugar: dejar el default o usar un helper privilegiado. No bloquear el MVP
  por esto.

### 4.8 Batería

- `power_supply` llamado `wiimote_battery_<MAC>` (con colones), propiedad
  `capacity` 0..100 [R2].
- Leer `capacity` dispara un status request al mando y espera la respuesta; no
  hacerlo por frame. Cada 30 s alcanza.

### 4.9 Speaker

**No soportado.** El enum de reportes de salida del driver no incluye los reportes
de speaker (`0x14`, `0x18`, `0x19`): solo tiene rumble `0x10`, LEDs `0x11`, DRM
`0x12`, IR `0x13`/`0x1a`, memoria `0x16`/`0x17` y status `0x15` [R3]. El protocolo
del speaker existe [R19], pero el driver no lo implementa. Usarlo requeriría
hidraw + protocolo propio + timing de 10 ms, y competiría con los output reports
del driver; no es una ruta razonable para este proyecto.

### 4.10 `hidraw`/`hidapi`: qué ofrece y por qué no

- `hid-wiimote` arranca el HID con `HID_CONNECT_HIDRAW` [R1], así que hay un
  `/dev/hidrawX` por Wiimote.
- `hidapi`/`hid` puede enumerar y leer ese hidraw, pero:
  - Los nodos hidraw son `root:root 0600` por defecto en este sistema; la regla
    `uaccess` de systemd solo etiqueta hidraw para ratones 3D, no para Wiimotes
    [R36]. Habría que agregar una regla udev propia.
  - Escribir output reports desde hidraw compite con el driver (rumble, LEDs,
    DRM, IR). El driver preserva el bit de rumble en sus reports, pero un writer
    externo tendría que hacer lo mismo y coordinar el estado.
  - Para leer los mismos datos que ya da evdev no aporta nada.
- **Único uso legítimo:** bypasear `hid-wiimote` (unbind) e implementar el
  protocolo completo para modo IR extended/full, speaker o control fino. Es la
  ruta de Dolphin/wiiuse, no la de este proyecto.

### 4.11 Sysfs útil

| Path | Contenido |
|---|---|
| `/sys/bus/hid/devices/<hid>/devtype` | `gen10`, `gen20`, `generic`, … [R1] |
| `/sys/bus/hid/devices/<hid>/extension` | `none`, `nunchuk`, `classic`, … [R1] |
| `/sys/bus/hid/devices/<hid>/uevent` | `HID_UNIQ` (MAC), `HID_PHYS`, `HID_ID` |
| `/sys/class/leds/<hid>:blue:pN/brightness` | LED de jugador N [R2] |
| `/sys/class/power_supply/wiimote_battery_<MAC>/capacity` | 0..100 [R2] |

`extension` acepta `scan` por escritura para forzar una re-detección (requiere
permisos de escritura) [R1]. No existe un atributo que diga “motionplus”: el MP
se detecta por el nodo evdev o por `dmesg` (`detected extension: Nintendo Wii
Motion Plus`) [R1].

---

## 5. Calibración, tasas, latencia y timestamps

### 5.1 Calibración del acelerómetro

El kernel no aplica la calibración de fábrica [R2]. Opciones:

1. **Empírica (recomendada para v1):** apoyar el mando quieto, promediar ~1 s de
   `ABS_RX/RY/RZ` y restar ese offset. Para escala, sostener cada eje vertical y
   medir el delta de 1 g; normalizar por eje. Es suficiente para tilt.
2. **EEPROM:** el Wiimote guarda 0 g y 1 g por eje en `0x16..0x29` [R19], pero
   no está expuesto por `hid-wiimote`. Leerlo requeriría hidraw + comandos
   `0x17`, que compite con el driver. No vale la pena para v1.

### 5.2 Calibración del MotionPlus

- En reposo, promediar ~1 s de `ABS_RX/RY/RZ` y restar el bias.
- Escala del driver: ~167.564 unidades/°/s [R2].
- El rango declarado es ±16000; con la escala del comentario, rotaciones rápidas
  podrían superarlo. Validar con hardware y no clampear a `absinfo.max` sin medir.

### 5.3 Calibración IR

- El EEPROM tiene 4 puntos de referencia para centro/escala/ángulo [R19], pero el
  driver no los aplica [R2].
- Para pointing, calibrar **pantalla**: mostrar 4 esquinas, capturar el midpoint
  de los 2 dots en cada una, y resolver una homografía 3×3. Es más directo y
  absorbe la geometría real de la barra/TV.
- Sin calibración, el midpoint ya sirve para pointing relativo; la separación
  entre dots correlaciona con distancia.

### 5.4 Tasa de reporte

- El Wiimote original (RVL-CNT-01) reporta a ~**100 Hz** [R19].
- El driver **no** pide reporte continuo: el comando DRM se manda con
  `cmd[1] = 0` [R1], y el bit 2 de ese byte es el “continuous reporting” [R19].
  Con acelerómetro/IR abiertos los valores cambian casi siempre, así que el
  flujo es ~100 Hz; con **solo botones** el Wiimote solo manda cuando cambia un
  botón (puede quedar en silencio).
- No asumir un período fijo: medir intervalos con los timestamps de evdev. El
  `fuzz` declarado (2 cuentas para accel/IR) también puede filtrar cambios
  pequeños [R2].

### 5.5 Timestamps

- evdev timestampa cada batch de eventos con `input_get_timestamp()`
  [R5][R6]. Por defecto el reloj del cliente evdev es **CLOCK_REALTIME**
  (`clk_type` cero = `INPUT_CLK_REAL`) [R5].
- El timestamp se toma cuando el batch llega a evdev, **no** cuando el paquete
  Bluetooth llega al adaptador. Es una mejora grande sobre timestampar a tiempo
  de frame (lo que hace Panda3D, §8), pero no es un timestamp de radio.
- Se puede pedir **CLOCK_MONOTONIC** con `EVIOCSCLOCKID` [R5] antes de empezar
  a leer; `python-evdev` no lo expone, pero se puede hacer con `fcntl.ioctl`.
  Así los timestamps son comparables con `time.monotonic()`:

```python
import fcntl, struct, time
EVIOCSCLOCKID = 0x400445A0  # _IOW('E', 0xa0, int)
fcntl.ioctl(dev.fd, EVIOCSCLOCKID, struct.pack("i", time.CLOCK_MONOTONIC))
```

- Cada input device (botones, accel, IR, MP) tiene su propio stream y su propio
  `SYN_REPORT`; no hay un sequence number común. Los eventos del mismo reporte
  HID llegan con timestamps casi idénticos; para fusionar, usar el timestamp y
  una ventana de unos pocos ms, o combinar a nivel de frame.

### 5.6 Latencia

No hay una medición de primera fuente de latencia Wiimote→Linux. Presupuesto
teórico:

| Etapa | Estimación | Fuente |
|---|---|---|
| Intervalo de reporte | ~10 ms (100 Hz) | [R19] (comunitario) |
| Transporte Bluetooth + HIDP + UHID | variable, pocos ms | no medido |
| Kernel → evdev → Python | sub-ms a unos ms | no medido |
| Cuantización de frame a 60 FPS | 0–16.7 ms | aritmética |
| **Total input→estado de juego** | **~10–35 ms** | **estimación, no medición** |

El target del proyecto (<50 ms) es plausible, pero **hay que medirlo** con el
hardware real. Métodos:

1. `evtest` para ver timestamps y confirmar la tasa.
2. Loguear `event.timestamp()` vs `time.monotonic()` al leer para medir la cola
   kernel→usuario (no incluye Bluetooth).
3. Para el total, filmar a 240 fps la pulsación y el cambio en pantalla, o usar
   un LED/fotodiodo; restar el refresh del display.

### 5.7 Hotplug y errores

- Al desconectarse el mando, `read_one()`/`read()` levanta `OSError` (`ENODEV`).
  Cerrar el fd, sacarlo del hub y re-escanear.
- Al reconectar, los nodos pueden cambiar de `/dev/input/eventN`; no cachear
  paths, re-escanear por nombre + `HID_UNIQ`.
- `SYN_DROPPED`: si la app se congela y el buffer evdev se llena, el kernel manda
  `SYN_DROPPED`. `python-evdev` no re-sincroniza solo; con 100 Hz y lectura por
  frame es raro, pero hay que loguearlo y, si pasa, reabrir el device.
- Si el mando se queda sin batería o se apaga, el HID device desaparece; los
  nodos LED/battery también.

---

## 6. IR: qué hay y qué necesita una barra DIY

### 6.1 Lo que entrega la cámara

- Hasta **4 puntos** IR trackeados, x 0..1023, y 0..767 (subpíxel 8×) [R19].
- **Sin imagen cruda**: la cámara tiene un procesador que solo entrega blobs [R19].
- Basic mode: 4 puntos x/y, **sin tamaño**. Extended: agrega tamaño 0..15.
  Full: agrega bounding box/intensidad. El driver solo usa basic [R2].
- FOV efectivo ~**33° horizontal × 23° vertical** (medido en una unidad) [R19].
  A 3 m: aprox. 1.8 m × 1.2 m de cobertura; suficiente para una TV típica,
  angosto si el mando se apunta muy de costado.
- Filtro IR: los LEDs de **940 nm** se detectan ~2× más que 850 nm con el filtro
  puesto [R19].

### 6.2 Barra DIY: mínimo y práctico

Lo mínimo para pointing de 2 puntos:

- **2 LEDs IR de 940 nm**, uno a cada lado, separados ~**20 cm** (la barra oficial
  usa 20 cm entre centros de cluster) [R19].
- 5 V (USB) + resistencia limitadora por LED. La documentación de Wiibrew no
  describe portadora para la cámara; las barras DIY estándar usan LEDs continuos.
- Apuntar los LEDs hacia el sofá, con la barra centrada arriba/abajo de la TV.

Mejoras:

- **2 LEDs por cluster (4 en total)**: más robustez/rango; la cámara trackea los
  4, y se puede promediar cada par. No es obligatorio.
- 850 nm funciona pero con menos intensidad; 940 nm es lo que espera el filtro.
- Evitar luz solar directa/incandescente fuerte en el campo de la cámara; puede
  meter blobs falsos.
- Si se usan 4 LEDs, separarlos para que la cámara los vea como 4 blobs y no se
  fusionen; el firmware puede switchear si hay más de 4 fuentes [R19].

### 6.3 Limitaciones con el driver estándar

1. **Solo basic mode**: no hay tamaño/intensidad para filtrar reflexiones.
2. **Sensibilidad fija nivel 3**: no hay sysfs para subir/bajar. El rango y la
   robustez dependen del brillo/geometría de los LEDs; hay que probarlo en la sala.
3. **Sin calibración IR de fábrica**: la app debe calibrar la pantalla.
4. **Sentinel `(1023, 1023)`**: filtrar slots vacíos (y puede exceder el rango
   nominal 0..767).
5. **Costo de energía**: abrir el nodo IR enciende la cámara; cerrarlo cuando no
   se usa [R2]. Ojo: si se usa Panda3D/ShowBase, su `InputDeviceManager` lo abre
   igual (ver §8.3).
6. Si se necesita full mode (bbox/intensidad) o control de sensibilidad, hay que
   bypassear `hid-wiimote` con hidraw y protocolo propio. No recomendado para v1.

### 6.4 Pointing con 2 dots (algoritmo)

```text
dots = [p0, p1] ordenados por x
mid  = ((x0+x1)/2, (y0+y1)/2)
sep  = hypot(x1-x0, y1-y0)
roll = atan2(y1-y0, x1-x0)

# Calibración: 4 esquinas -> homografía H (3x3)
u, v, w = H @ [mid.x, mid.y, 1]
pointer = (u/w, v/w)          # normalizado 0..1
distance ≈ k / sep            # calibrable; no es necesario para pointing 2D
```

- `sep` sirve para detectar distancia y para normalizar el midpoint si la barra
  no está perfectamente paralela a la pantalla.
- Un solo dot alcanza para pointing absoluto si la distancia es fija, pero no da
  roll ni distancia; con 2 dots se tiene todo.
- Filtrar con One Euro o media móvil; a 100 Hz se puede suavizar sin agregar
  latencia perceptible.

---

## 7. Librerías Python: estado y compatibilidad

| Librería | Versión / fecha | Python 3.13/3.14 | Estado | Veredicto |
|---|---|---|---|---|
| **`evdev`** (`python-evdev`) | 2.0.0, 2026-08-23 | Sí (>=3.11; free-threaded) [R20][R21] | Activa [R24]; **solo sdist**, compila C [R20] | **Primaria** |
| `libevdev` (`python-libevdev`) | 0.13.1, 2025-11-14 | Sí (>=3.9; wheel `py3-none-any`) [R25] | Activa, upstream libevdev | Alternativa si molesta compilar; sin helpers FF |
| `hid` (ctypes) | 1.0.9, 2026-02-05 | Sí (pure Python) [R30] | Activa | Solo avanzado |
| `hidapi` (Cython) | 0.15.0, 2025-12-09 | Sí (cp314 wheels) [R31] | Activa [R29] | Solo avanzado |
| `PyBluez` | 0.23, 2019-12-28 [R32] | No confiable | Muerta | No |
| `cwiid` | 3.0.0, 2017-04-30 [R33] | No confiable | Muerta | No |
| `xwiimote` (C) | repo, 2024 [R34] | N/A (C) | Poco activa | No |
| `wiiuse` (C) | repo activo 2026 [R39] | N/A (C) | Activa | No para esta stack |
| `dbus-fast` | 5.2.0, 2026-10-02 | Sí (cp314) [R37] | Activa | Opcional (wizard) |
| `pyudev` | 0.24.5, 2026-09-28 | Sí (>=3.10) [R38] | Activa | Opcional (hotplug) |

Notas de compatibilidad:

- **`evdev` 2.0.0 se compiló e importó correctamente en un venv con Python
  3.14.8 en este equipo** (verificación local). No publica wheels: `pip install
  evdev` compila la extensión C; hacen falta `gcc` y headers de Python. Para
  distribuir (AppImage/Flatpak/paquete), construir en el bundle o vendorizar un
  wheel.
- El changelog de 2.0.0 agrega soporte para modo free-threaded y el parámetro
  `readonly` [R21]. El mínimo es 3.11, así que 3.13/3.14 están cubiertos.
- La documentación de `python-evdev` avisa que la funcionalidad de FF está
  “básica” y no fue suficientemente ejercitada [R22]. El rumble del Wiimote es
  simple (binario), pero **hay que probarlo con hardware**.
- **`libevdev` 0.13.1** es una alternativa interesante si no se quiere compilar:
  wheel puro Python, requiere `libevdev` del sistema (instalado aquí: 1.14.0).
  Maneja `SYN_DROPPED` y estado del device mejor que `python-evdev`, pero no vi
  helpers de force feedback en su API; para rumble habría que usar ioctl/raw.
- **Panda3D 1.10.16** tiene wheels cp314 [R28] y se importó correctamente en este
  equipo con Python 3.14.8 (verificación local). No es un bloqueante.
- `PyBluez` no aporta nada: emparejar es trabajo de BlueZ, no de la app.
- `xwiimote`/`cwiid`/`wiiuse` duplican lo que ya hace `hid-wiimote` y agregan
  dependencias C; no se justifican.

---

## 8. Integración con Panda3D

### 8.1 Panda3D ya soporta evdev, pero no sirve para el Wiimote

Panda3D 1.10+ tiene soporte nativo de evdev/joystick [R26]:
`base.devices.get_devices(InputDevice.DeviceClass.gamepad)`,
`attachInputDevice`, `find_button`, `find_axis`, `set_vibration`, etc. Para un
gamepad USB estándar funciona bien. Para el Wiimote, no:

1. **Timestamps a tiempo de frame.** `EvdevInputDevice::process_events()` hace
   `double time = ClockObject::get_global_clock()->get_frame_time();` y usa ese
   valor para todos los eventos del batch [R27]. No usa el timestamp del kernel.
   A 60 FPS, cada evento queda cuantizado al frame; se pierde la información de
   los 100 Hz para integrar motion.
2. **Clasificación.** El input device de botones del Wiimote no tiene
   `BTN_GAMEPAD` ni `ABS_X`, y su nombre no dice “gamepad”; los heuristics de
   Panda3D lo dejan en `unknown` (no `gamepad`) [R27]. Los botones/ejes se pueden
   leer, pero no por la API pensada para gamepads.
3. **IR incompleto.** El mapeo de `ABS_HAT` de Panda3D solo contempla
   `ABS_HAT0X/Y` y `ABS_HAT2X/Y` (y este último solo para el quirk de Steam
   Controller); `ABS_HAT1*` y `ABS_HAT3*` se ignoran [R27]. HAT0 se convierte en
   D-pad, no en ejes de pointing; en la práctica no se pueden leer los 4 dots
   como pares de ejes.
4. **Sin MAC.** `InputDevice` no expone `uniq`/MAC; `serial_number` se lee de
   sysfs USB, no de `HID_UNIQ` [R27]. Con varios Wiimotes no hay forma limpia de
   saber qué nodo pertenece a qué mando.
5. **Acelerómetro/MP con semántica de gamepad.** `ABS_RX/RY/RZ` se mapean a
   right-stick/yaw, no a “aceleración”.
6. **Abre todos los nodos, incluido el IR.** `ShowBase` inicializa el
   `InputDeviceManager` global [R41], y en Linux el `LinuxInputDeviceManager`
   escanea `/dev/input/event*`, abre cada device legible y lo mantiene abierto
   [R40][R27]. Eso incluye el nodo IR del Wiimote: al abrirlo, el kernel llama a
   `wiimod_ir_open` y enciende la cámara IR aunque el juego no la use, con el
   costo de batería correspondiente [R2]. No hay una opción de config para
   excluir un device; es un efecto secundario de usar ShowBase.

**Conclusión:** usar el evdev nativo de Panda3D para teclado/mouse y, si acaso,
gamepads USB; para el Wiimote, un poller propio con `python-evdev`. Y tener en
cuenta que ShowBase va a abrir los nodos del Wiimote de todos modos.

### 8.2 Poller recomendado (sin thread)

Para 60 FPS, lo más simple y determinista es drenar evdev **una vez por frame**,
al principio del frame, antes de la lógica del juego:

```python
from direct.showbase.ShowBase import ShowBase
from direct.task import Task


class App(ShowBase):
    def __init__(self, wiimote_hub):
        super().__init__()
        self.hub = wiimote_hub
        # sort negativo = corre antes que la lógica del juego
        self.taskMgr.add(self.poll_input, "poll-wiimote", sort=-100)

    def poll_input(self, task):
        self.hub.poll()                 # drena todos los fds no bloqueantes
        frame = self.hub.latest_frame() # ControllerFrame inmutable
        self.game.on_controller_frame(frame)
        return Task.cont
```

Ventajas:

- Sin locks ni threads; el estado se actualiza en el mismo hilo que Panda3D.
- A 100 Hz entran ~1.7 reportes por frame; se drenan todos y se puede integrar
  motion con los timestamps.
- Latencia máxima: un frame (16.7 ms a 60 FPS) + transporte. Para el target de
  <50 ms, el presupuesto debería alcanzar, pero hay que medirlo con hardware.

Si más adelante se necesita reaccionar entre frames (menú, UI), se puede mover a
un thread con `select` y un snapshot lock; no es necesario para v1.

En modo kiosco, `dev.grab()` sobre los nodos del Wiimote evita que el compositor
u otras apps reaccionen a los `KEY_*` del D-pad/±; liberar con `ungrab()` al
salir (el grab se libera solo si el proceso muere).

### 8.3 El costo oculto: Panda3D abre el nodo IR

Aunque el juego lea el Wiimote por fuera, `ShowBase` ya creó el
`InputDeviceManager` global y su implementación Linux abre **todos** los
`/dev/input/event*` legibles [R40][R41]. Consecuencias:

- El nodo IR se abre al conectar el mando (o en el próximo `update()`), el
  driver enciende la cámara [R2] y la batería del Wiimote se consume aunque el
  juego no use pointing.
- Los nodos de acelerómetro y MotionPlus también quedan abiertos, así que el
  DRM incluye esos datos; no es un problema funcional (el poller propio puede
  leer los mismos eventos), pero sí de consumo.
- No hay `ConfigVariable` para excluir devices en 1.10.16; las mitigaciones son:
  aceptar el costo (si el proyecto va a usar IR, no importa), compilar Panda3D
  sin soporte de input Linux, o correr el input en un proceso auxiliar con
  permisos y dejar el proceso del juego sin acceso a los nodos del Wiimote (esto
  último es mucho más complejo y no se recomienda para v1).

Para el MVP, **aceptar** que la cámara IR queda encendida si el mando está
conectado, o desconectar el Wiimote cuando no se juega. Medir el consumo real
antes de optimizar.

### 8.4 `ControllerFrame`

Identificadores en inglés, datos normalizados:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ControllerFrame:
    timestamp: float                  # CLOCK_MONOTONIC del evento más reciente
    source: str                       # "wiimote" | "android"
    connected: bool
    buttons: frozenset[str]           # {"a","b","1","2","plus","minus","home","up",...}
    accel: tuple[float, float, float] # g (calibrado) o cuentas normalizadas
    gyro: tuple[float, float, float] | None  # deg/s (si hay MotionPlus)
    pointer: tuple[float, float] | None      # 0..1 (si hay IR calibrada)
    battery: int | None               # 0..100
```

- `buttons` como set: fácil de mapear a acciones y de testear.
- `pointer` solo si el IR está abierto y calibrado; si no, `None` y el juego usa
  el pointer del celular.
- `connected=False` para mandos que se desconectaron; el hub conserva el slot.
- El hub debe setear `CLOCK_MONOTONIC` (o convertir) para que `timestamp` sea
  comparable con `time.monotonic()`; si no, usar solo diferencias de timestamps.

---

## 9. Proof of concept y snippets

En el repo se incluye `research/wiimote_probe.py`, un script de diagnóstico sin
dependencias fuera de `evdev`:

```bash
python research/wiimote_probe.py list
python research/wiimote_probe.py dump --seconds 10
python research/wiimote_probe.py rumble --ms 200
```

### 9.1 Descubrir mandos y MAC

```python
import os
import evdev


def hid_uniq(event_path: str) -> str | None:
    """MAC del Wiimote a partir del HID parent (sirve para UHID y HIDP)."""
    name = os.path.basename(event_path)  # "event12"
    uevent = f"/sys/class/input/{name}/device/device/uevent"
    try:
        with open(uevent, encoding="ascii") as fh:
            for line in fh:
                if line.startswith("HID_UNIQ="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        return None
    return None


def scan_wiimotes() -> dict[str, dict[str, evdev.InputDevice]]:
    found: dict[str, dict[str, evdev.InputDevice]] = {}
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except OSError:
            continue
        if not dev.name.startswith("Nintendo Wii Remote"):
            continue
        mac = hid_uniq(path) or "unknown"
        found.setdefault(mac, {})[dev.name] = dev
    return found
```

`evdev.list_devices()` solo devuelve devices legibles; si la lista está vacía,
revisar permisos (§10).

### 9.2 Drenar eventos (núcleo del poller)

```python
from evdev import ecodes

KEYS = {
    ecodes.BTN_A: "a",
    ecodes.BTN_B: "b",
    ecodes.BTN_1: "1",
    ecodes.BTN_2: "2",
    ecodes.BTN_MODE: "home",
    ecodes.KEY_NEXT: "plus",
    ecodes.KEY_PREVIOUS: "minus",
    ecodes.KEY_UP: "up",
    ecodes.KEY_DOWN: "down",
    ecodes.KEY_LEFT: "left",
    ecodes.KEY_RIGHT: "right",
}

IR_EMPTY = (1023, 1023)  # slot vacío: 10 bits en 1 (y excede el máximo nominal 767)


class Wiimote:
    def __init__(self, mac: str, nodes: dict[str, "evdev.InputDevice"]):
        self.mac = mac
        self.keys = nodes.get("Nintendo Wii Remote")
        self.accel = nodes.get("Nintendo Wii Remote Accelerometer")
        self.ir = nodes.get("Nintendo Wii Remote IR")
        self.mp = nodes.get("Nintendo Wii Remote Motion Plus")
        self.pressed: set[str] = set()
        self.accel_xyz = (0, 0, 0)
        self.gyro_xyz = None
        self.dots: list[tuple[int, int] | None] = [None] * 4

    def poll(self) -> None:
        for kind, dev in (("keys", self.keys), ("accel", self.accel),
                          ("ir", self.ir), ("mp", self.mp)):
            if dev is None:
                continue
            while True:
                try:
                    ev = dev.read_one()
                except OSError:
                    return  # ENODEV: el hub debe re-escanear
                if ev is None:
                    break
                self._handle(kind, ev)

    def _handle(self, kind: str, ev) -> None:
        if ev.type == ecodes.EV_KEY and ev.value in (0, 1):
            name = KEYS.get(ev.code)
            if name:
                (self.pressed.add if ev.value else self.pressed.discard)(name)
        elif ev.type == ecodes.EV_ABS:
            if kind == "accel":
                # llegan RX, RY, RZ; guardamos el último valor de cada uno
                idx = {ecodes.ABS_RX: 0, ecodes.ABS_RY: 1, ecodes.ABS_RZ: 2}.get(ev.code)
                if idx is not None:
                    acc = list(self.accel_xyz)
                    acc[idx] = ev.value
                    self.accel_xyz = tuple(acc)
            elif kind == "mp":
                idx = {ecodes.ABS_RX: 0, ecodes.ABS_RY: 1, ecodes.ABS_RZ: 2}.get(ev.code)
                if idx is not None:
                    gyro = list(self.gyro_xyz or (0, 0, 0))
                    gyro[idx] = ev.value
                    self.gyro_xyz = tuple(gyro)
            elif kind == "ir":
                code = ev.code - ecodes.ABS_HAT0X
                slot, axis = divmod(code, 2)
                if 0 <= slot < 4 and axis in (0, 1):
                    dot = list(self.dots[slot] or (0, 0))
                    dot[axis] = ev.value
                    self.dots[slot] = (dot[0], dot[1]) if tuple(dot) != IR_EMPTY else None
```

Notas:

- `read_one()` no bloquea; devuelve `None` cuando no hay más eventos.
- `IR_EMPTY` se filtra al construir el dot. Un punto parcial (solo X o Y) queda
  como `(x,0)` hasta que llega el otro eje; en la práctica llegan juntos en el
  mismo `SYN_REPORT`.
- Si el device se desconecta, `read_one()` puede levantar `OSError`; el hub debe
  cerrar y re-escanear.

### 9.3 Rumble

```python
from evdev import ecodes, ff


def pulse(dev: "evdev.InputDevice", duration_ms: int = 120) -> None:
    effect = ff.Effect(
        type=ecodes.FF_RUMBLE,
        id=-1,
        direction=0,
        ff_trigger=ff.Trigger(button=0, interval=0),
        ff_replay=ff.Replay(length=duration_ms, delay=0),
        u=ff.EffectType(
            ff_rumble_effect=ff.Rumble(strong_magnitude=0xFFFF, weak_magnitude=0xFFFF)
        ),
    )
    effect_id = dev.upload_effect(effect)   # 2.0.0 escribe el id en effect.id
    dev.write(ecodes.EV_FF, effect_id, 1)
    # para cortar antes: dev.write(ecodes.EV_FF, effect_id, 0)
```

El Wiimote ignora la magnitud: cualquier valor no-cero prende el motor [R2]. Si
`upload_effect` falla con `EINVAL`/`EPERM`, el fd se abrió read-only; abrir el
device principal con `O_RDWR` (o dar permisos rw).

### 9.4 LEDs y batería

```python
import glob
import os


def hid_dir_for_mac(mac: str) -> str | None:
    for hdev in glob.glob("/sys/bus/hid/devices/*"):
        try:
            with open(os.path.join(hdev, "uevent"), encoding="ascii") as fh:
                txt = fh.read()
        except OSError:
            continue
        if f"HID_UNIQ={mac}" in txt:
            return hdev
    return None


def set_player_led(mac: str, player: int) -> None:  # player 1..4
    hdev = hid_dir_for_mac(mac)
    if not hdev:
        return
    base = os.path.basename(hdev)
    for i in range(4):
        path = f"/sys/class/leds/{base}:blue:p{i}/brightness"
        try:
            with open(path, "w", encoding="ascii") as fh:
                fh.write("1" if i == player - 1 else "0")
        except OSError:
            pass


def battery_percent(mac: str) -> int | None:
    path = f"/sys/class/power_supply/wiimote_battery_{mac}/capacity"
    try:
        with open(path, encoding="ascii") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None
```

### 9.5 Verificar el tipo de mando y MotionPlus

```bash
cat /sys/bus/hid/devices/0005:057E:0306.*/devtype   # gen10
cat /sys/bus/hid/devices/0005:057E:0330.*/devtype   # gen20 (MP integrado)
cat /sys/bus/hid/devices/0005:057E:0306.*/extension # none/nunchuk/classic/...
dmesg | grep -i 'wiimote\|Motion Plus'
```

Si hay un dongle MotionPlus externo, el nodo `Nintendo Wii Remote Motion Plus`
aparece hasta 4 s después; no hay atributo sysfs que lo nombre.

---

## 10. Riesgos y problemas conocidos

| Riesgo | Evidencia | Mitigación |
|---|---|---|
| BlueZ 5.73–5.79 mandaba PIN `0000` y rompía el pairing | [R14], fix en 5.80 [R12] | Usar 5.87; verificar `wii_pincb` en el binario; no bajar a 5.7x. |
| `1+2` no crea bond y BlueZ 5.87 lo rechaza por `ClassicBondedOnly=true` | [R8][R9] | Usar red sync. Si se necesita guest: `ClassicBondedOnly=false` y `connect` sin `pair`. |
| `pair` en `1+2` falla por PIN incorrecto | [R7][R19] | No parear en `1+2`; el PIN de BlueZ es el del host, el de `1+2` es el del Wiimote. |
| `RVL-CNT-01-TR` se apaga si el HID se abre antes de autenticar | [R19] | Red sync (bond + autenticación) y conectar el HID después; evitar `1+2`. |
| `RVL-CNT-01-TR` se desconecta en algunos kernels/BlueZ | [R16] (cerrado sin causa concluyente) | Probar el kernel/distro objetivo; el reporte menciona que CachyOS funcionaba, pero no es evidencia controlada. |
| UHID (default) tuvo regresiones | [R14] | 5.87 incluye el merge de autopair; si `hid-wiimote` no bindea, probar `UserspaceHID=false` y reiniciar Bluetooth. |
| `evdev` no publica wheels y compila C | [R20] | Pin 2.0.0; build en CI/bundle; o evaluar `libevdev` (wheel puro) si el FF se resuelve aparte. |
| FF de `python-evdev` poco ejercitado | [R22] | Probar rumble con hardware; fallback a ioctl `EVIOCSFF`/`write` o al FF nativo de Panda3D. |
| Permisos de `/dev/input/event*` | [R35][R36] | uaccess de logind suele aplicar porque los nodos se clasifican joystick; si no, `input` group o regla udev. |
| Permisos de hidraw son root por defecto | [R36] + verificación local | Evitar hidapi; si se usa, regla udev propia. |
| IR solo basic, sensibilidad fija, sin calibración | [R2][R19] | Aceptar 4 dots x/y; calibrar pantalla; no prometer tamaño/intensidad. |
| Acelerómetro sin calibrar | [R2][R19] | Calibración empírica al inicio; no integrar para posición. |
| MP: escala/rango declarado inconsistente | [R2] | Medir con hardware; no clampear a ±16000 sin validar. |
| Speaker no soportado | [R3][R19] | No incluirlo en el diseño; audio por la TV/PC. |
| Múltiples Wiimotes con el mismo nombre | [R1][R2] | Agrupar por `HID_UNIQ`; parear de a uno; LEDs manuales en 7.2.15 (requieren root). |
| Clones/terceros con otro VID/PID | [R1] | `hid-wiimote` solo matchea `057e:0306`/`057e:0330`; un clon con otro ID cae en `hid-generic` y no expone sensores. Usar un mando Nintendo real. |
| Latencia real desconocida | sin medición primaria | Medir con `evtest` + filmación/led; no asumir <50 ms sin datos. |
| `hid-wiimote` no bindea en un kernel custom | config del kernel | Verificar `CONFIG_HID_WIIMOTE`, `CONFIG_BT_HIDP`, `CONFIG_INPUT_FF_MEMLESS`; `modprobe hid-wiimote`. |
| ShowBase abre el nodo IR y enciende la cámara | [R40][R41][R2] | Aceptar el costo de batería, compilar Panda3D sin input Linux, o usar un proceso auxiliar; no hay config para excluir devices. |

---

## 11. Preguntas abiertas / validación pendiente

1. **Revisión exacta del mando del usuario:** ¿`RVL-CNT-01` (0x0306) o
   `RVL-CNT-01-TR` (0x0330)? ¿Tiene MotionPlus integrado o dongle? El `devtype`
   y el nodo MP lo responden.
2. **Pairing real con BlueZ 5.87 + esta unidad:** el código y los reportes dicen
   que red sync debería funcionar; falta probarlo. Si falla, capturar `btmon` y
   verificar que `wii_pincb` se ejecuta.
3. **Tasa y jitter reales:** medir intervalos de `SYN_REPORT` con `evtest`/
   `wiimote_probe.py dump`; confirmar ~100 Hz y ver si el modo change-driven
   genera gaps.
4. **Latencia input→frame:** medir con filmación de alta velocidad o LED; el
   presupuesto de 10–35 ms es una estimación.
5. **IR bar:** decidir 2 vs 4 LEDs, geometría (20 cm), alimentación y calibración;
   validar el rango y el FOV en la sala real.
6. **MotionPlus:** si existe, validar escala/bias y si el rango declarado alcanza
   para rotaciones rápidas.
7. **Permisos en la sesión real:** confirmar que logind aplica uaccess a los nodos
   del Wiimote cuando se lanza el juego desde el escritorio Wayland; si no,
   agregar regla udev/`input` group.
8. **Empaquetado:** cómo se distribuye `evdev` (build en CI, wheel propio,
   Flatpak/AppImage).
9. **Panda3D + Iris Xe a 60 FPS:** fuera de este ticket, pero el input asume que
   el frame loop es estable.

---

## 12. Referencias

Cada referencia indica qué soporta. Las fuentes de kernel y BlueZ son el código
exacto de las versiones auditadas; Wiibrew es documentación comunitaria de
reverse engineering (no oficial de Nintendo), usada también por el driver.

- **[R1]** Linux `v7.2.15`, `drivers/hid/hid-wiimote-core.c`.
  <https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/hid/hid-wiimote-core.c?h=v7.2.15>
  — detección de device type, selección de DRM, creación de input devices,
  sysfs `devtype`/`extension`, polling de MotionPlus, tabla de IDs
  `057e:0306`/`057e:0330`.
- **[R2]** Linux `v7.2.15`, `drivers/hid/hid-wiimote-modules.c`.
  <https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/hid/hid-wiimote-modules.c?h=v7.2.15>
  — mapeo de botones, acelerómetro, IR (basic, ABS_HAT, sensibilidad),
  MotionPlus (escala), rumble, LEDs, batería.
- **[R3]** Linux `v7.2.15`, `drivers/hid/hid-wiimote.h`.
  <https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/hid/hid-wiimote.h?h=v7.2.15>
  — enum de reportes de salida (no hay speaker), flags de protocolo.
- **[R4]** Linux `v7.2.15`, `net/bluetooth/hidp/core.c`.
  <https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/net/bluetooth/hidp/core.c?h=v7.2.15>
  — HIDP setea `bus=BUS_BLUETOOTH` y `uniq=dst` (MAC del Wiimote).
- **[R5]** Linux `v7.2.15`, `drivers/input/evdev.c`.
  <https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/input/evdev.c?h=v7.2.15>
  — timestamps de evdev, `EVIOCSCLOCKID`, default CLOCK_REALTIME.
- **[R6]** Linux `v7.2.15`, `drivers/input/input.c`.
  <https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/input/input.c?h=v7.2.15>
  — `input_set_timestamp`, reset en SYN, semántica del timestamp.
- **[R7]** BlueZ `5.87`, `plugins/autopair.c`.
  <https://github.com/bluez/bluez/blob/5.87/plugins/autopair.c>
  — comentarios de red sync vs `1+2`, `wii_pincb`, PIN = dirección del adaptador.
- **[R8]** BlueZ `5.87`, `profiles/input/device.c`.
  <https://github.com/bluez/bluez/blob/5.87/profiles/input/device.c>
  — `classic_bonded_only = true`, rechazo de no-bonded, UHID, chequeo de
  reconexión.
- **[R9]** BlueZ `5.87`, `profiles/input/input.conf`.
  <https://github.com/bluez/bluez/blob/5.87/profiles/input/input.conf>
  — defaults `UserspaceHID=true`, `ClassicBondedOnly=true`.
- **[R10]** BlueZ `5.87`, `src/shared/uhid.c`.
  <https://github.com/bluez/bluez/blob/5.87/src/shared/uhid.c>
  — UHID `bus=BUS_BLUETOOTH`, `phys`/`uniq`.
- **[R11]** BlueZ `5.87`, `profiles/input/manager.c`.
  <https://github.com/bluez/bluez/blob/5.87/profiles/input/manager.c>
  — `input` profile `auto_connect=true`, config `ClassicBondedOnly`.
- **[R12]** BlueZ commit `c281bc4608` (2025-01-07), “autopair: Move handling of
  wii controllers”.
  <https://github.com/bluez/bluez/commit/c281bc4608>
  — merge de `wii_pincb` en autopair; incluido desde 5.80 (comparar con
  `plugins/autopair.c` en el tag 5.79 vs 5.80).
- **[R13]** BlueZ commit `7679c96954` (2025-01-07), “build: Remove wiimote
  plugin”.
  <https://github.com/bluez/bluez/commit/7679c96954>
  — eliminación del plugin separado.
- **[R14]** BlueZ issue #911, “Wiimote Bluetooth pairing does not work above
  5.72”.
  <https://github.com/bluez/bluez/issues/911>
  — regresión 5.73–5.79, diagnóstico del orden de plugins, mención de UHID.
- **[R15]** BlueZ issue #1395, “Unable to pair Wii remote (Authentication
  Failed)” (abierto).
  <https://github.com/bluez/bluez/issues/1395>
  — reportes de auth failure, red sync vs `1+2`, workaround `-P autopair` en
  versiones viejas.
- **[R16]** BlueZ issue #1762, “Nintendo RVL-CNT-01-TR … will not stay
  connected”.
  <https://github.com/bluez/bluez/issues/1762>
  — desconexión de TR; cerrado sin causa concluyente.
- **[R17]** BlueZ D-Bus `org.bluez.Device1` API.
  <https://github.com/bluez/bluez/blob/5.87/doc/org.bluez.Device.rst>
  — `Pair`, `Connect`, `Trusted`, `Paired`, `Connected`.
- **[R18]** BlueZ D-Bus `org.bluez.Adapter1` API.
  <https://github.com/bluez/bluez/blob/5.87/doc/org.bluez.Adapter.rst>
  — `StartDiscovery`, `StopDiscovery`.
- **[R19]** Wiibrew, “Wiimote”.
  <https://wiibrew.org/wiki/Wiimote>
  — pairing/PIN, `1+2` guest, single-press reconnect, formatos de reporte,
  acelerómetro/ADXL330, cámara IR (128×96, 4 dots, 1024×768, FOV 33×23, 20 cm,
  940 nm, modos basic/extended/full, sensibilidad), EEPROM/calibración, speaker,
  tasa de ~100 Hz. Documentación comunitaria, no oficial.
- **[R20]** PyPI, `evdev` 2.0.0.
  <https://pypi.org/project/evdev/>
  — versión, `requires_python >=3.11`, solo sdist.
- **[R21]** Python-evdev changelog.
  <https://python-evdev.readthedocs.io/en/latest/changelog.html>
  — 2.0.0: free-threaded, `readonly`, `writeback_id`, mínimo 3.11.
- **[R22]** Python-evdev, “Scope and status”.
  <https://python-evdev.readthedocs.io/en/latest/scope.html>
  — FF “basic”, no suficientemente ejercitado; uinput sin FF.
- **[R23]** Python-evdev tutorial, “Uploading FF-effects”.
  <https://python-evdev.readthedocs.io/en/latest/tutorial.html>
  — ejemplo de `ff.Effect`, `upload_effect`, `EV_FF`.
- **[R24]** Python-evdev GitHub.
  <https://github.com/gvalkov/python-evdev>
  — actividad/maintenance.
- **[R25]** PyPI, `libevdev` 0.13.1.
  <https://pypi.org/project/libevdev/>
  — wheel `py3-none-any`, >=3.9, wrapper de libevdev.
- **[R26]** Panda3D manual, “Joystick Support”.
  <https://docs.panda3d.org/1.10/python/programming/hardware-support/joystick-support>
  — soporte evdev nativo desde 1.10, device classes, nota de `input` group.
- **[R27]** Panda3D `v1.10.16`, `panda/src/device/evdevInputDevice.cxx`.
  <https://github.com/panda3d/panda3d/blob/v1.10.16/panda/src/device/evdevInputDevice.cxx>
  — timestamp a `get_frame_time()` (línea 799), mapeo `ABS_HAT` (604–645),
  heuristics de device class.
- **[R28]** PyPI, `panda3d` 1.10.16.
  <https://pypi.org/project/panda3d/>
  — wheels cp313/cp314, Linux x86_64.
- **[R29]** libusb/hidapi.
  <https://github.com/libusb/hidapi>
  — librería C hidapi, actividad.
- **[R30]** PyPI, `hid` 1.0.9.
  <https://pypi.org/project/hid/>
  — bindings ctypes, pure Python.
- **[R31]** PyPI, `hidapi` 0.15.0.
  <https://pypi.org/project/hidapi/>
  — bindings Cython, wheels cp314.
- **[R32]** PyPI, `PyBluez` 0.23.
  <https://pypi.org/project/PyBluez/>
  — último release 2019.
- **[R33]** PyPI, `cwiid` 3.0.0.
  <https://pypi.org/project/cwiid/>
  — último release 2017.
- **[R34]** xwiimote (C) repo y HOWTO.
  <https://github.com/xwiimote/xwiimote> ·
  <https://github.com/xwiimote/xwiimote/issues/3>
  — diagnóstico, IR vía evdev, log de `wiimote` bindeado sobre UHID.
- **[R35]** systemd, `src/udev/udev-builtin-input_id.c`.
  <https://github.com/systemd/systemd/blob/main/src/udev/udev-builtin-input_id.c>
  — heurísticas `ID_INPUT_JOYSTICK` (botones/ejes).
- **[R36]** systemd, `rules.d/70-uaccess.rules.in`.
  <https://github.com/systemd/systemd/blob/main/rules.d/70-uaccess.rules.in>
  — `uaccess` solo para `ID_INPUT_JOYSTICK`; no para hidraw genérico.
- **[R37]** PyPI, `dbus-fast` 5.2.0.
  <https://pypi.org/project/dbus-fast/>
  — wheels cp314, cliente D-Bus async.
- **[R38]** PyPI, `pyudev` 0.24.5.
  <https://pypi.org/project/pyudev/>
  — binding libudev, hotplug.
- **[R39]** wiiuse (C).
  <https://github.com/wiiuse/wiiuse>
  — librería C cross-platform con protocolo propio.
- **[R40]** Panda3D `v1.10.16`, `panda/src/device/linuxInputDeviceManager.cxx`.
  <https://github.com/panda3d/panda3d/blob/v1.10.16/panda/src/device/linuxInputDeviceManager.cxx>
  — escanea `/dev/input`, abre cada `event*` legible y crea `EvdevInputDevice`.
- **[R41]** Panda3D `v1.10.16`, `direct/src/showbase/ShowBase.py`.
  <https://github.com/panda3d/panda3d/blob/v1.10.16/direct/src/showbase/ShowBase.py>
  — `self.devices = InputDeviceManager.getGlobalPtr()` y `self.devices.update()`
  por frame.

---

## Apéndice A: comandos de diagnóstico

```bash
# Versiones y módulos
bluetoothctl --version
uname -r
modinfo hid-wiimote
sudo modprobe hid-wiimote   # normalmente autoload por modalias
lsmod | grep -E 'hid_wiimote|hidp|ff_memless|uhid'

# Tras conectar el Wiimote
dmesg | tail -50
ls -l /sys/bus/hid/drivers/wiimote/
cat /sys/bus/hid/devices/*/uevent | grep -E 'HID_NAME|HID_UNIQ|HID_PHYS'

# Nodos evdev
ls -l /dev/input/by-id/ | grep -i nintendo
evtest            # paquete "evtest"; elegir "Nintendo Wii Remote"

# Estado BlueZ
bluetoothctl info XX:XX:XX:XX:XX:XX
bluetoothctl show

# Diagnóstico de pairing
sudo btmon        # en otra terminal, mientras se hace pair
```

## Apéndice B: checklist de validación con hardware

- [ ] `bluetoothctl` 5.87 y `wii_pincb` presente en el binario.
- [ ] Red sync + `pair`/`trust`/`connect`; `info` con `Bonded: yes`.
- [ ] `dmesg` muestra `wiimote ... New device registered` y
      `detected device: Nintendo Wii Remote (Gen 1/Plus)`.
- [ ] Aparecen los nodos `Nintendo Wii Remote`, `Accelerometer`, `IR` y,
      si hay MP, `Motion Plus`.
- [ ] `wiimote_probe.py list` muestra MAC y paths.
- [ ] `wiimote_probe.py dump` confirma ~100 Hz y botones correctos.
- [ ] Rumble responde; LEDs cambian; `capacity` devuelve 0..100.
- [ ] Reconnect: apagar el mando, presionar un botón, ver el nodo reaparecer.
- [ ] Medir latencia y jitter reales.
- [ ] Si hay IR bar: calibrar 4 esquinas y validar pointing a 2–4 m.
