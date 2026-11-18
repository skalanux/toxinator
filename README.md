# Toxinator 3

Consola personal de juegos 3D en Python, con mandos intercambiables (Wiimote original + celular Android) y juegos originales. El primer juego es **Maldito Pino**, un bolos con pinos con actitud.

## Estado

El **mapa de decisiones** está completo en el issue [#1](https://github.com/skalanux/toxinator/issues/1): arquitectura, input, render, física, launcher, i18n y testing. Cada decisión cerrada está en su ticket y resumida en el mapa.

Ya corren tres cortes: el **launcher LIGA** (`toxinator`), **Maldito Pino** (`toxinator play maldito-pino`) y el banco de input (`toxinator dev phone`). La PWA del mando se puede instalar, se vincula escaneando el QR y cambia sola entre **LAUNCHER** y **JUEGO**. El Wiimote, i18n y el hot-seat de 1–4 jugadores todavía no están integrados.

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
  QR (desde la cámara o desde la propia PWA).
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
- **Mouse**: los botones también responden.

Al elegir **JUGAR**, el launcher cede la pantalla al juego; **Esc** en el juego
vuelve a la liga. El servidor del celular sigue vivo entre launcher y juego.

La PWA tiene **dos pantallas** y cambia sola según el modo:

- **LAUNCHER**: joystick grande + **A / ELEGIR**; sin sensores. Arrastrás para
  mover el foco y soltás en el centro.
- **JUEGO**: apuntar con touch, efecto con inclinación, **A / ACCIÓN** y
  calibración; los sensores y el readout vuelven a aparecer.

### Instalar el mando y vincularlo

La PWA se puede instalar y abrir sin pasar por el navegador. Si la abrís sin
token (por ejemplo, desde el icono instalado) o el vínculo venció, muestra
**VINCULAR MANDO**:

1. Arrancá la consola: si no hay ningún mando, el QR aparece solo. También podés
   abrirlo con **SUMAR CELULAR** o la tecla **C**.
2. En la PWA, **ESCANEAR QR** pide permiso de cámara y vincula la consola.
   También podés tocar **INGRESAR DATOS** y escribir `IP:puerto` + token.
3. La PWA guarda host y token en `localStorage`; la próxima apertura reconecta
   sola. **CAMBIAR** vuelve a la pantalla de vinculación (por ejemplo, si cambió
   la IP o el token de la consola).

Abrir directamente la URL del QR (`https://IP:8443/?token=...`) también vincula:
la PWA guarda el token y limpia la URL.

La instalación completa (WebAPK en Android) necesita que Chrome confíe en el
certificado. Con el certificado autofirmado puede quedar solo como **acceso
directo** y el service worker no se registra. Para una instalación real, usá un
certificado local confiable con `mkcert`:

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
QR (`--host` si usás un nombre). `--cert` y `--key` también funcionan en
`toxinator play` y `toxinator dev phone`. Si tu versión de Android no confía en
la CA de usuario, la alternativa es publicar la consola por un túnel HTTPS con
certificado público.

Por defecto, el token cambia cada vez que arranca la consola. Si la PWA queda en
**Token inválido**, volvé a escanear el QR desde la propia app (no hace falta
reinstalarla).

### Si la PWA no encuentra la consola

- Asegurate de que `uv run toxinator` siga corriendo y no hayas cerrado la
  terminal: si la consola se apaga, el servidor también.
- Confirmá que el celular está en la misma Wi-Fi, sin datos móviles ni VPN.
- La IP de la consola puede cambiar. El QR de la consola es la fuente de verdad:
  escaneá el QR actual. **RECONECTAR** usa la IP guardada; si cambió, no alcanza.
- Abrí `https://IP:8443/` en el navegador del celular y aceptá el certificado.
  En la PWA podés usar **ABRIR CONSOLA**. Esto suele hacer falta cuando la PWA
  quedó instalada desde otra IP.
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
3. Abrí la URL del QR en el celular y aceptá el aviso de certificado
   autofirmado. El token de la URL vincula la consola automáticamente.
4. Si abrís la PWA sin token (o desde el icono instalado), tocá **ESCANEAR QR**
   y apuntá al QR que la consola muestra sola al arrancar (o abrilo con **C** /
   **SUMAR CELULAR**); también podés usar **INGRESAR DATOS**. Permití la cámara
   y los sensores.
5. Incliná el teléfono o tocá la pantalla para mover la bola de P1. **A** es el
   botón de acción; **Calibrar** toma la pose actual como neutra.

El servidor usa un certificado autofirmado en `~/.config/toxinator/dev-cert`; si
cambia la IP de la LAN, se regenera solo. La PWA vive en `controller-web/` y se
sirve desde el mismo origen que el WebSocket, para que la excepción del
certificado cubra ambos.

Opciones útiles:

```bash
uv run toxinator dev phone --demo                 # P1 sintético, sin celular
uv run toxinator dev phone --headless --demo      # servidor + estado por consola
uv run toxinator dev phone --offscreen --screenshot /tmp/toxinator.png
uv run toxinator dev phone --host 192.168.0.141 --port 8443
```

En esta etapa el único mando es el celular; Wiimote y gamepad entran en los
siguientes cortes.

## Maldito Pino jugable

```bash
uv sync --all-packages
uv run toxinator play maldito-pino
```

El juego abre con el QR en el terminal. Desde el celular:

- **Arrastrá** en el touchpad para apuntar.
- **Incliná** el teléfono para dar efecto.
- **Mantené A** para cargar potencia y **soltá** para tirar.
- **Calibrar** toma la pose actual como neutra: la lectura β/γ vuelve a 0 y aparece **Pose guardada**. Si el pie dice **SENSORES OFF**, tocá **Activar sensores** primero.

Es un corte de **un jugador**: 10 turnos, plenos/spares, 10º turno con bonus y
marcador. Hot-seat de 1–4, práctica y desempate quedan para el siguiente corte.
La física usa los parámetros validados en #16 (bola 7 kg, pinos 1.5 kg, CCD,
1/120).

Sin celular, para ver la escena y el auto-juego:

```bash
uv run toxinator play maldito-pino --demo
uv run toxinator play maldito-pino --demo --offscreen --screenshot /tmp/pino.png
```

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
- `aiohttp` para HTTPS + WebSocket del controlador
- `qrcode` para el QR del terminal
- Bullet para física (Maldito Pino y prototipo)
- Wiimote por `hid-wiimote` + `python-evdev` (pendiente)
- Celular Android por PWA HTTPS + WSS (primer corte)
