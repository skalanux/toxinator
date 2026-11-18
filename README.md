# Toxinator 3

Consola personal de juegos 3D en Python, con mandos intercambiables (Wiimote original + celular Android) y juegos originales. El primer juego es **Maldito Pino**, un bolos con pinos con actitud.

## Estado

El **mapa de decisiones** está completo en el issue [#1](https://github.com/skalanux/toxinator/issues/1): arquitectura, input, render, física, launcher, i18n y testing. Cada decisión cerrada está en su ticket y resumida en el mapa.

Ya corren tres cortes: el **launcher LIGA** (`toxinator`), **Maldito Pino** (`toxinator play maldito-pino`) y el banco de input (`toxinator dev phone`). El mando del celular funciona por **HTTP/WS sin certificado**; con HTTPS se puede instalar la PWA y usar la cámara. La PWA cambia sola entre **LAUNCHER** y **JUEGO**. Los juegos nuevos pueden vivir fuera del repo, en `~/Projects/toxinator-games`. El Wiimote, i18n y el hot-seat de 1–4 jugadores todavía no están integrados.

## Documentos

- [GLOSSARY.md](GLOSSARY.md): vocabulario canónico.
- [AGENTS.md](AGENTS.md): cómo trabajan los agentes en este repo.
- [docs/adr/](docs/adr/): decisiones de arquitectura.
- [docs/design/launcher-liga.md](docs/design/launcher-liga.md): identidad y estructura del launcher (**LIGA · Noche**).
- [docs/design/i18n.md](docs/design/i18n.md): internacionalización, catálogos y cambio de idioma en runtime.
- [docs/design/testing.md](docs/design/testing.md): simulador de mandos, trazas y CI headless.
- [docs/testing/manual-checklist.md](docs/testing/manual-checklist.md): validación con Wiimote, Android, GPU y performance.
- [docs/agents/](docs/agents/): configuración de issue tracker y dominio.

## Research

Los findings están en branches `research/*` (no se mergean):

| Branch | Tema |
|---|---|
| `research/wiimote-linux` | Wiimote en Linux: pairing, HID y sensores |
| `research/python-3d-engine` | Panda3D vs alternativas |
| `research/android-phone-controller` | Celular Android como mando |

Para leerlos:

```bash
git fetch origin research/wiimote-linux research/python-3d-engine research/android-phone-controller
git show origin/research/wiimote-linux:research/wiimote-linux.md
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

## Launcher LIGA

```bash
uv sync --all-packages
uv run toxinator
```

Abre **LIGA · Noche**, la pantalla de inicio de la consola:

- **Contendiente destacado**: Maldito Pino, con rank, evento, récord, formatos y
  los botones **JUGAR** y **FICHA**.
- **Próximos desafíos**: Kart y Tenis como contendientes futuros.
- **Plantel**: los 4 slots; el celular aparece como P1 cuando se vincula con el
  QR (con la cámara del teléfono o, en HTTPS, desde la propia PWA).
- **Ajustes** y **sumar celular** con el **QR en pantalla** y la URL de la sesión.
- Si no hay ningún mando conectado, el launcher abre el QR de vinculación
  automáticamente. No hace falta teclado ni mouse para el primer vínculo: la
  pantalla se cierra sola cuando el celular se conecta. **VOLVER** (o **Esc**)
  permite explorar la liga con teclado/mouse y **C** vuelve a abrir el QR.

Controles:

- **Flechas**: navegar.
- **Enter**: elegir / jugar.
- **D**: ficha del desafío.
- **S**: ajustes.
- **C**: sumar celular y ver el QR.
- **Esc**: volver o cerrar la liga.
- **Touchpad del celular**: joystick para mover el foco.
- **A del celular**: confirma el foco actual.
- **B del celular**: cierra el overlay actual o vuelve a la liga desde el juego.
- **Mouse**: los botones también responden.

Al elegir **JUGAR**, el launcher cede la pantalla al juego; **Esc** en el juego o
**B / VOLVER** en el celular vuelven a la liga. El servidor del celular sigue
vivo entre launcher y juego.

La PWA tiene **dos pantallas** y cambia sola según el modo:

- **LAUNCHER**: joystick grande + **A / ELEGIR** + **B / ATRÁS**; sin sensores.
  Arrastrás para mover el foco y soltás en el centro. **B** cierra FICHA,
  AJUSTES o la pantalla de vinculación; en la pantalla principal devuelve el
  foco a JUGAR.
- **JUEGO**: apuntar con touch, efecto con inclinación, **A / ACCIÓN**,
  **B / VOLVER** a la liga y calibración; los sensores y el readout vuelven a
  aparecer.

### Conectar el celular (modo HTTP, sin certificado)

Por defecto la consola sirve el mando por **HTTP/WS**, sin TLS. No hay aviso de
certificado y no hace falta instalar nada:

1. Arrancá `uv run toxinator`. Si no hay ningún mando, el QR aparece solo en la
   pantalla (también podés abrirlo con **SUMAR CELULAR** o **C**).
2. Escaneá el QR con la **cámara del teléfono** y abrí el enlace. La URL lleva el
   token; la PWA se vincula sola.
3. Cuando el celular se conecta, la pantalla de la consola se cierra y la PWA
   pasa a **LAUNCHER**.

En HTTP funcionan el touchpad, **A**, el launcher y los juegos. No funcionan la
cámara interna de la PWA, la instalación como app ni (según el navegador) los
sensores. Es un modo para tu LAN: el tráfico no va cifrado.

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
en `toxinator play` y `toxinator dev phone`. Si tu versión de Android no confía en
la CA de usuario, la alternativa es publicar la consola por un túnel HTTPS con
certificado público.

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
uv run toxinator launcher --demo --offscreen --screenshot /tmp/liga.png
```

## Primer corte: `toxinator dev phone`

1. Conectá el celular Android a la misma Wi-Fi que la consola.
2. Corré `uv run toxinator dev phone`.
3. Abrí la URL del QR en el celular. En el modo HTTP por defecto no hay aviso de
   certificado: el token de la URL vincula la consola automáticamente.
4. Si abrís la PWA sin token, escaneá el QR con la cámara del teléfono y abrí el
   enlace, o usá **INGRESAR DATOS**. La cámara interna y **ESCANEAR QR** de la
   PWA necesitan `--https`; en HTTP no están disponibles.
5. Tocá la pantalla para mover la bola de P1. **A** es el botón de acción;
   **Calibrar** toma la pose actual como neutra. Con HTTPS, además, podés
   inclinar el teléfono para dar efecto.

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
```

En esta etapa el único mando es el celular; Wiimote y gamepad entran en los
siguientes cortes.

## Maldito Pino jugable

```bash
uv sync --all-packages
uv run toxinator play maldito-pino
```

El juego abre con el QR en el terminal. Por defecto usa **HTTP**, así que abrí el
enlace en el navegador del celular sin aceptar certificado. Desde el celular:

- **Arrastrá** en el touchpad para apuntar.
- **Mantené A** para cargar potencia y **soltá** para tirar.
- **B / VOLVER** corta el juego y vuelve a la liga.
- **Calibrar** toma la pose actual como neutra: la lectura β/γ vuelve a 0 y aparece **Pose guardada**. Si el pie dice **SENSORES OFF**, tocá **Activar sensores** primero.
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

Para arrancar desde el template:

```bash
cd ~/Projects/toxinator-games
cp -r _template mi-juego
mv mi-juego/src/template_game mi-juego/src/mi_juego
cd /home/ska/Projects/toxinator
uv run toxinator play mi-juego
```

El launcher de la LIGA sigue mostrando la cartelera curada del repo; los juegos
externos se lanzan por id con `toxinator play`. La guía completa está en
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

- `prototype/launcher-ux`: launcher **LIGA · Noche**.
- `prototype/bowling-physics`: física de pinos y tuning de bolos. Informe en
  `prototype/bowling-physics.md` del branch; video y mediciones incluidos.

## Stack

- Python 3.14
- Panda3D 1.10.16 (XWayland)
- `aiohttp` para HTTP/HTTPS + WebSocket del controlador
- `qrcode` para el QR del terminal
- Bullet para física (Maldito Pino y prototipo)
- Wiimote por `hid-wiimote` + `python-evdev` (pendiente)
- Celular Android por HTTP/WS por defecto; PWA HTTPS/WSS opcional
