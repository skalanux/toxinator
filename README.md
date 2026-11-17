# Toxinator 3

Consola personal de juegos 3D en Python, con mandos intercambiables (Wiimote original + celular Android) y juegos originales. El primer juego es **Maldito Pino**, un bolos con pinos con actitud.

## Estado

El proyecto está en fase de diseño. El **mapa de decisiones** y la frontera actual viven en el issue [#1](https://github.com/skalanux/toxinator/issues/1). Cada decisión cerrada está en su ticket y resumida en el mapa.

El repo todavía **no tiene código ejecutable**: contiene el mapa, el glosario, los ADRs, el diseño del launcher y la documentación de agentes. Los comandos de la sección **Desarrollo** son el objetivo del primer corte, no algo que ya funcione.

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

## Desarrollo (planificado)

```bash
uv sync
uv run toxinator
uv run toxinator dev phone
uv run pytest
uv run ruff check
uv run mypy
```

El primer corte es `toxinator dev phone`: QR + PWA + WSS + InputHub + escena 3D mínima, con el celular Android como mando.

## Continuar desde otra máquina

```bash
git clone git@github.com:skalanux/toxinator.git
cd toxinator
```

Abrí el [mapa #1](https://github.com/skalanux/toxinator/issues/1), leé **Decisions so far** y tomá el primer ticket de la frontera. La sesión de chat no se transfiere; los artefactos y el estado del mapa sí.

## Stack

- Python 3.14
- Panda3D 1.10.16 (XWayland)
- Bullet para física
- Wiimote por `hid-wiimote` + `python-evdev`
- Celular Android por PWA HTTPS + WSS
