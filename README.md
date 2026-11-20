# Toxinator 3

Consola personal de juegos 3D en Python, con el celular como mando y teclado/mouse como simulador, y juegos originales. El primer juego es **Maldito Pino**, un bolos con pinos con actitud.

## Estado

El **mapa de decisiones** está completo en el issue [#1](https://github.com/skalanux/toxinator/issues/1): arquitectura, input, render, física, launcher, i18n y testing. Cada decisión cerrada está en su ticket y resumida en el mapa.

Ya corren tres cortes: el **launcher de Toxinator** (`toxinator`), **Maldito Pino** (`toxinator play maldito-pino`) y el banco de input (`toxinator dev phone`). El mando del celular funciona por **HTTP/WS sin certificado**; con HTTPS se puede instalar la PWA y usar la cámara. La PWA cambia sola entre **LAUNCHER** y **JUEGO**. Los juegos nuevos pueden vivir fuera del repo, en `~/Projects/toxinator-games`. El mando v2 (botones PlayStation, landscape/vertical, panel por juego y foto para avatares) está especificado en [docs/design/controller-v2.md](docs/design/controller-v2.md); i18n y el hot-seat de 1–4 jugadores todavía no están integrados.

## Documentos

- [GLOSSARY.md](GLOSSARY.md): vocabulario canónico.
- [AGENTS.md](AGENTS.md): cómo trabajan los agentes en este repo.
- [docs/adr/](docs/adr/): decisiones de arquitectura.
- [docs/adr/0007-phone-controller-v2.md](docs/adr/0007-phone-controller-v2.md): mando v2, fin del Wiimote y simulador de teclado/mouse.
- [docs/adr/0008-avatar-from-photo.md](docs/adr/0008-avatar-from-photo.md): avatares 3D locales desde foto.
- [docs/design/controller-v2.md](docs/design/controller-v2.md): anatomía, perfil por juego y protocolo del mando v2.
- [docs/design/launcher-toxinator.md](docs/design/launcher-toxinator.md): pantalla de inicio, catálogo y paleta Tokyo Night.
- [docs/design/i18n.md](docs/design/i18n.md): internacionalización, catálogos y cambio de idioma en runtime.
- [docs/design/testing.md](docs/design/testing.md): simulador de mandos, trazas y CI headless.
- [docs/testing/manual-checklist.md](docs/testing/manual-checklist.md): validación con Android, teclado/mouse, GPU y performance.
- [docs/agents/](docs/agents/): configuración de issue tracker y dominio.

## Research

Los findings están en branches `research/*` (no se mergean):

| Branch | Tema |
|---|---|
| `research/python-3d-engine` | Panda3D vs alternativas |
| `research/android-phone-controller` | Celular Android como mando |

Para leerlos:

```bash
git fetch origin research/python-3d-engine research/android-phone-controller
git show origin/research/android-phone-controller:research/android-phone-controller.md
```

## Desarrollo

```bash
uv sync --all-packages
uv run toxinator
uv run toxinator play maldito-pino
uv run toxinator dev phone
uv run pytest
uv run ruff check
uv run mypy
```

## Launcher

```bash
uv sync --all-packages
uv run toxinator
```

Abre la pantalla de inicio de **Toxinator**, un catálogo navegable con:

- **Rail lateral**: Inicio, Catálogo, Mandos y Ajustes, con reloj, fecha y el
  estado de los cuatro controles.
- **Juego destacado**: arte, descripción, jugadores, formatos y los botones
  **Jugar** y **Ficha**. El arte es un diorama isométrico; `[art] motif` en el
  manifest elige el prop.
- **Tus juegos**: la fila de juegos instalados y del catálogo; al mover el foco
  por una tarjeta cambia el juego destacado.
- **Catálogo**: grilla filtrable por *Todos*, *Instalados*, *Para varios* y
  *Próximamente*, con paginación cuando hay más de ocho juegos.
- **Ficha**: arte grande, descripción, jugadores, formatos, id y estado.
- **Mandos**: estado de P1–P4 y botón para vincular el celular con QR. El mando
  puede cambiar de layout, orientación, etiquetas, panel y cámara según el juego
  (`[controller]` en el manifest); el jugador puede bloquear la orientación desde
  los ajustes. Los juegos pueden hacer vibrar el celular y reproducir tonos
  cortos por el parlante; el mando muestra un aviso **ACTIVAR SONIDO Y
  VIBRACIÓN** para habilitarlo con un toque. Para vibración usá Chrome o Samsung
  Internet en Android; Firefox Android no vibra desde la web.
- **Ajustes**: paleta Tokyo Night, idioma y salida de la consola.
- Si no hay ningún mando conectado, el launcher abre el QR de vinculación
  automáticamente. **Esc** permite explorar con teclado/mouse y **C** vuelve a
  abrir el QR.

Controles:

- **Flechas**: navegar con el simulador de teclado.
- **Enter o J**: elegir / jugar / abrir ficha (×).
- **Esc o K**: volver o cerrar el overlay (○).
- **D**: ficha del juego destacado.
- **S**: ajustes.
- **C**: vincular celular y ver el QR.
- **Mouse**: apuntar y hacer clic; el botón izquierdo confirma y el derecho vuelve.
- **Stick del celular**: mover el foco.
- **× del celular**: confirma el foco actual.
- **○ del celular**: cierra el overlay actual o vuelve al launcher desde el juego.

Al elegir **Jugar**, el launcher cede la pantalla al juego; **○ / VOLVER** en el
celular vuelve al launcher. El servidor del celular sigue vivo entre launcher y
juego.

El teclado/mouse entra como **simulador de mando** (`--no-keyboard` lo apaga,
`--keyboard-slot` elige el slot, por defecto P5). Se puede jugar sin celular.

La PWA tiene **dos pantallas** y cambia sola según el modo:

- **LAUNCHER**: stick izquierdo + **× / ELEGIR** + **○ / ATRÁS**; sin sensores
  ni readout. El stick es relativo y vuelve al centro al soltar. **○** cierra
  FICHA, MANDOS, AJUSTES o la pantalla de vinculación; en la pantalla principal
  devuelve el foco a **Jugar**.
- **JUEGO**: × ○ □ △, `options`, `L1`/`R1`, stick izquierdo y zona táctil
  derecha para apuntar. El mando funciona en landscape y vertical; el perfil del
  juego puede pedir una orientación. El gesto principal debería ser movimiento;
  el puntero queda como apoyo.
- Los **ajustes** del mando (⋯) tienen orientación, sensores, calibrar, skin y
  telemetría. La telemetría muestra β/γ/ACC/RTT y viene oculta por defecto.
- Si el juego declara `panel`, el mando muestra una imagen estática (mapa,
  referencia) que se puede expandir. Si declara `camera`, aparece el botón de
  foto; requiere HTTPS.

### Conectar el celular (modo HTTP, sin certificado)

Por defecto la consola sirve el mando por **HTTP/WS**, sin TLS. No hay aviso de
certificado y no hace falta instalar nada:

1. Arrancá `uv run toxinator`. Si no hay ningún mando, el QR aparece solo en la
   pantalla (también podés abrirlo con **SUMAR CELULAR** o **C**).
2. Escaneá el QR con la **cámara del teléfono** y abrí el enlace. La URL lleva el
   token; la PWA se vincula sola.
3. Cuando el celular se conecta, la pantalla de la consola se cierra y la PWA
   pasa a **LAUNCHER**.

En HTTP funcionan el stick, el touch, **×**, el launcher y los juegos. No
funcionan la cámara interna de la PWA, la foto de avatar, la instalación como app
ni (según el navegador) los sensores. Es un modo para tu LAN: el tráfico no va
cifrado.

Abrir directamente `http://IP:8443/?token=...` también vincula y guarda el token.

### PWA instalable y cámara (HTTPS)

Para instalar la PWA o usar **ESCANEAR QR** dentro de la app, serví con HTTPS:

```bash
uv run toxinator launcher --https   # autofirmado: aceptá el aviso una vez
```

La PWA arranca en **VINCULAR MANDO** si no hay token. Ahí podés escanear el QR
con la cámara del celular desde la propia app, o **INGRESAR DATOS**. La app
guarda host y token en `localStorage`; **CAMBIAR** vuelve a la vinculación.

La instalación completa (WebAPK en Android) necesita que Chrome confíe en el
certificado. Con el autofirmado puede quedar solo como **acceso directo** y el
service worker no se registra. Para una instalación real, usá un certificado
local confiable con `mkcert` (implica HTTPS):

```bash
mkcert -install
mkdir -p ~/.config/toxinator
mkcert -cert-file ~/.config/toxinator/lan.pem \
       -key-file ~/.config/toxinator/lan-key.pem 192.168.0.141

uv run toxinator launcher \
  --cert ~/.config/toxinator/lan.pem \
  --key ~/.config/toxinator/lan-key.pem
```

En Android, instalá el archivo `rootCA.pem` que está dentro de la carpeta que
imprime `mkcert -CAROOT`, como **certificado de CA de usuario** desde Ajustes →
Seguridad. Después abrí `https://192.168.0.141:8443/` una vez y verificá el
candado. La IP o el nombre del certificado tienen que coincidir con el host del
QR (`--host` si usás un nombre). `--https`, `--cert` y `--key` también funcionan
en `toxinator play` y `toxinator dev phone`.

### Túnel Cloudflare (`--cloudflare`)

Si no querés tocar la CA del teléfono, la consola puede crear un **Cloudflare
Quick Tunnel** con certificado válido:

```bash
sudo pacman -S cloudflared   # una vez
uv run toxinator --cloudflare
```

La consola levanta el servidor local, arranca `cloudflared tunnel --url` y usa
la URL pública `https://...trycloudflare.com` para el QR. Sensores, cámara y PWA
funcionan porque el origen es HTTPS válido.

- Necesita conexión a internet y `cloudflared` en el PATH.
- La URL es temporal y cambia en cada arranque.
- Agrega latencia; para jugar en la misma LAN, `mkcert` es más rápido.
- `--cloudflare` no se combina con `--https`, `--cert` ni `--key`.
- También está disponible en `toxinator play --cloudflare` y
  `toxinator dev phone --cloudflare`.
- La URL incluye el token de sesión; no la compartas fuera de tu red.

Por defecto, el token cambia cada vez que arranca la consola. Si la PWA queda en
**Token inválido**, volvé a escanear el QR (no hace falta reinstalarla).

### Si el celular no encuentra la consola

- Asegurate de que `uv run toxinator` siga corriendo y no hayas cerrado la
  terminal: si la consola se apaga, el servidor también.
- Confirmá que el celular está en la misma Wi-Fi, sin datos móviles ni VPN.
- La IP de la consola puede cambiar. El QR de la consola es la fuente de verdad:
  escaneá el QR actual. **RECONECTAR** usa la IP guardada; si cambió, no alcanza.
- En **HTTP** abrí `http://IP:8443/` en el navegador del celular. No hay
  certificado que aceptar. No uses el icono de una PWA HTTPS vieja: el navegador
  bloquea `ws://` desde una página HTTPS. Si Chrome intenta cambiar solo a
  `https://`, elegí **Continuar al sitio** o desactivá **Usar siempre conexiones
  seguras** para esa red.
- En **HTTPS** abrí `https://IP:8443/` y aceptá el certificado. En la PWA podés
  usar **ABRIR CONSOLA**. Esto suele hacer falta cuando la PWA quedó instalada
  desde otra IP.
- Si el navegador del celular tampoco abre la URL, revisá el firewall del equipo
  y el aislamiento de clientes del router:

  ```bash
  sudo ufw status | grep 8443
  sudo ufw allow 8443/tcp
  ```

- Para que no vuelva a pasar, reservá la IP de la consola en el router o usá un
  hostname estable con `--host`.

```bash
uv run toxinator launcher --demo        # P1 sintético
uv run toxinator launcher --demo --offscreen --screenshot /tmp/launcher.png
```

## Primer corte: `toxinator dev phone`

1. Conectá el celular Android a la misma Wi-Fi que la consola.
2. Corré `uv run toxinator dev phone`.
3. Abrí la URL del QR en el celular. En el modo HTTP por defecto no hay aviso de
   certificado: el token de la URL vincula la consola automáticamente.
4. Si abrís la PWA sin token, escaneá el QR con la cámara del teléfono y abrí el
   enlace, o usá **INGRESAR DATOS**. La cámara interna y **ESCANEAR QR** de la
   PWA necesitan `--https`; en HTTP no están disponibles.
5. Movete con el stick izquierdo, apuntá con la zona táctil y usá **×** como
   acción. Los ajustes (⋯) muestran el readout y **Calibrar**, que toma la pose
   actual como neutra. Con HTTPS, además, podés inclinar el teléfono para dar
   efecto.

Por defecto el servidor es **HTTP/WS** y no genera certificado. Con `--https` usa
un certificado autofirmado en `~/.config/toxinator/dev-cert`; con `--cert/--key`
usa uno de confianza. La PWA vive en `controller-web/` y se sirve desde el mismo
origen que el WebSocket.

Opciones útiles:

```bash
uv run toxinator dev phone --demo                 # P1 sintético, sin celular
uv run toxinator dev phone --headless --demo      # servidor + estado por consola
uv run toxinator dev phone --offscreen --screenshot /tmp/toxinator.png
uv run toxinator dev phone --host 192.168.0.141 --port 8443
uv run toxinator dev phone --https                # PWA/cámara (autofirmado)
uv run toxinator dev phone --no-keyboard          # sin simulador de teclado/mouse
```

En esta etapa el mando es el celular; el teclado/mouse funciona como simulador
para manejar la consola y jugar sin teléfono. El Wiimote quedó descartado
([ADR-0007](docs/adr/0007-phone-controller-v2.md)).

## Maldito Pino jugable

```bash
uv sync --all-packages
uv run toxinator play maldito-pino
```

El juego abre con el QR en el terminal. Por defecto usa **HTTP**, así que abrí el
enlace en el navegador del celular sin aceptar certificado. Desde el celular:

- **Arrastrá** en la zona táctil para apuntar (o movés el mouse en la consola).
- **Mantené ×** para cargar potencia y **soltá** para tirar.
- **○ / VOLVER** corta el juego y vuelve al launcher.
- **Calibrar** (ajustes ⋯) toma la pose actual como neutra: la lectura β/γ vuelve a 0 y aparece **Pose guardada**. Si dice **SENSORES OFF**, tocá **Activar** primero.
- Con `--https`, además podés **inclinar** el teléfono para dar efecto.

Para la PWA instalable y los sensores por HTTPS:

```bash
uv run toxinator play maldito-pino --https
```

Es un corte de **un jugador**: 10 turnos, plenos/spares, 10º turno con bonus y
marcador. Hot-seat de 1–4, práctica y desempate quedan para el siguiente corte.
La física usa los parámetros validados en #16 (bola 7 kg, pinos 1.5 kg, CCD,
1/120).

Sin celular, para ver la escena y el auto-juego:

```bash
uv run toxinator play maldito-pino --demo
uv run toxinator play maldito-pino --demo --offscreen --screenshot /tmp/pino.png
```

## Juegos externos

Los juegos nuevos no necesitan vivir en este repo. Por defecto la consola
descubre paquetes en:

```text
~/Projects/toxinator-games/
```

También podés apuntar a otra ruta:

```bash
export TOXINATOR_GAMES_DIR=/ruta/a/mis-juegos
```

Cada juego es un paquete source-only:

```text
mi-juego/src/mi_juego/
├── __init__.py      # create_game(manifest)
├── manifest.toml
└── game.py
```

El cargador agrega `src/` al `sys.path`, importa el paquete y llama
`create_game(manifest)`. No se instala nada; el juego usa el venv de la consola.

Para crear el esqueleto de un juego e instalarlo:

```bash
uv run toxinator new mi-juego          # crea ./mi-juego/
uv run toxinator install mi-juego      # symlink en ~/Projects/toxinator-games
uv run toxinator play mi-juego
```

`new` arma `src/<módulo>/manifest.toml`, `__init__.py`, `game.py`, un
`pyproject.toml`, un README y una copia del skill
`.opencode/skills/toxinator-game-dev/` para que un agente tenga la guía de
desarrollo dentro del juego; acepta `--dir` para elegir el directorio destino y
`--name` para el nombre visible. `install` toma un directorio con
`src/<módulo>/manifest.toml` (por defecto, el actual) y lo enlaza en el
directorio de juegos externos. Todavía no copia archivos ni instala paquetes
Python: es un symlink. `--force` reemplaza un symlink existente, nunca un
directorio real.

También podés partir del template de `~/Projects/toxinator-games/_template` si
preferís el flujo manual.

Los juegos externos aparecen en la **biblioteca** del launcher al iniciar y se
pueden lanzar con **× / ENTER** o desde el celular. También podés lanzarlos
directo por id:

```bash
uv run toxinator play mi-juego
```

Para que el launcher los vea, reiniciá la consola después de crear o cambiar el
`manifest.toml`. La guía completa está en
`~/Projects/toxinator-games/README.md` y el skill de desarrollo en
[`.opencode/skills/toxinator-game-dev/SKILL.md`](.opencode/skills/toxinator-game-dev/SKILL.md).

Los juegos son código Python: cargá solo juegos de fuentes confiables.

## Continuar desde otra máquina

```bash
git clone git@github.com:skalanux/toxinator.git
cd toxinator
```

Abrí el [mapa #1](https://github.com/skalanux/toxinator/issues/1), leé **Decisions so far** y la sección **Frontier**. El mapa de decisiones está completo; sigue la implementación. La sesión de chat no se transfiere; los artefactos y el estado del mapa sí.

## Prototipos

Los prototipos viven en branches y no se mergean:

- `prototype/bowling-physics`: física de pinos y tuning de bolos. Informe en
  `prototype/bowling-physics.md` del branch; video y mediciones incluidos.

## Stack

- Python 3.14
- Panda3D 1.10.16 (XWayland)
- `aiohttp` para HTTP/HTTPS + WebSocket del controlador
- `qrcode` para el QR del terminal
- Bullet para física (Maldito Pino y prototipo)
- Celular Android por HTTP/WS por defecto; PWA HTTPS/WSS opcional
- Teclado/mouse como simulador de mando (`KeyboardMouseSource`)
