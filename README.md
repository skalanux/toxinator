# Toxinator 3

Consola personal de juegos 3D en Python, con mandos intercambiables (Wiimote original + celular Android) y juegos originales. El primer juego es **Maldito Pino**, un bolos con pinos con actitud.

## Estado

El **mapa de decisiones** está completo en el issue [#1](https://github.com/skalanux/toxinator/issues/1): arquitectura, input, render, física, launcher, i18n y testing. Cada decisión cerrada está en su ticket y resumida en el mapa.

Ya corren tres cortes: el **launcher LIGA** (`toxinator`), **Maldito Pino** (`toxinator play maldito-pino`) y el banco de input (`toxinator dev phone`). El Wiimote, i18n y el hot-seat de 1–4 jugadores todavía no están integrados.

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
- **Plantel**: los 4 slots; el celular aparece como P1 cuando escanea el QR del
  terminal.
- **Ajustes** y **sumar celular** con la URL de la sesión.

Controles:

- **Flechas**: navegar.
- **Enter**: elegir / jugar.
- **D**: ficha del desafío.
- **S**: ajustes.
- **Esc**: volver o cerrar la liga.
- **A del celular**: confirma el foco actual.
- **Mouse**: los botones también responden.

Al elegir **JUGAR**, el launcher cede la pantalla al juego; **Esc** en el juego
vuelve a la liga. El servidor del celular sigue vivo entre launcher y juego.

```bash
uv run toxinator launcher --demo        # P1 sintético
uv run toxinator launcher --offscreen --screenshot /tmp/liga.png
```

## Primer corte: `toxinator dev phone`

1. Conectá el celular Android a la misma Wi-Fi que la consola.
2. Corré `uv run toxinator dev phone`.
3. Escaneá el QR del terminal.
4. Aceptá el aviso de certificado autofirmado y permití los sensores.
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
