# Integración y testing

Fuente de verdad: `src/toxinator/core/external_games.py`,
`src/toxinator/core/games.py`, `src/toxinator/dev/play.py`,
`src/toxinator/dev/projects.py`, `src/toxinator/cli.py`, `pyproject.toml` y
`~/Projects/toxinator-games/README.md`.

## Directorio externo

Por defecto el cargador busca:

```text
~/Projects/toxinator-games/
├── README.md
├── _template/                 # no se carga: empieza con _
└── mi-juego/
    └── src/
        └── mi_juego/
            ├── __init__.py    # create_game(manifest)
            ├── manifest.toml
            └── game.py
```

`TOXINATOR_GAMES_DIR` sobreescribe la ruta:

```bash
export TOXINATOR_GAMES_DIR=/ruta/a/mis-juegos
```

El scanner busca `*/src/*/manifest.toml`, sigue symlinks (así funciona
`toxinator install`), ignora nombres que empiezan con `.` o `_`, agrega
`<juego>/src` al `sys.path`, importa el paquete y exige:

```python
def create_game(manifest: GameManifest) -> Game: ...
```

Ventajas:

- No hay que instalar el juego en el venv.
- El juego puede vivir en otro repo/directorio.
- Se puede editar y volver a lanzar la consola sin recompilar.

Límites:

- El nombre del módulo (`mi_juego`) debe ser único; el `sys.path` compartido no
  resuelve colisiones de nombres.
- Usa el venv de la consola; dependencias extra se instalan ahí.
- Es código Python confiable: no cargues juegos de terceros no confiables.
- Los juegos externos aparecen en la **biblioteca** del launcher al iniciar y
  también se lanzan con `toxinator play <id>`. Si creás o cambiás un juego,
  reiniciá la consola para que lo vea.
- Un juego roto se loguea y se ignora; no tumba el resto.

## Crear e instalar

`toxinator new` genera el esqueleto y `toxinator install` lo deja disponible
para la consola:

```bash
cd /home/ska/Projects/toxinator
uv run toxinator new mi-juego          # ./mi-juego/
uv run toxinator install mi-juego      # symlink en el directorio de juegos
uv run toxinator play mi-juego
```

- `new <id> [--dir PADRE] [--name "Mi Juego"]`: crea
  `PADRE/<id>/{README.md,pyproject.toml,.opencode/skills/toxinator-game-dev/,src/<módulo>/{__init__.py,manifest.toml,game.py}}`.
  `PADRE` por defecto es el directorio actual. El id debe empezar con minúscula
  y usar solo minúsculas, números, `-` o `_`; el módulo reemplaza `-` por `_`.
  Nunca escribe en un directorio con contenido (un directorio vacío sí vale).
  El skill se copia desde `.opencode/skills/toxinator-game-dev/` del repo de la
  consola; si no se encuentra, `new` falla sin dejar el juego a medias.
- `install [RUTA] [--force]`: lee `RUTA/src/*/manifest.toml` (RUTA por defecto
  `.`), toma el `id` del manifest y crea `games_dir()/<id> -> RUTA`. Es un
  symlink relativo: no copia archivos ni instala paquetes Python. Repetirlo es
  idempotente. `--force` reemplaza otro symlink, nunca un directorio real. Si el
  juego ya vive dentro de `games_dir()`, no hay nada que enlazar.

El template manual `~/Projects/toxinator-games/_template/` sigue existiendo como
referencia, pero el flujo recomendado es `new` + `install`. El template muestra
el contrato mínimo: `start` crea raíces, `update` lee `input_state`, `stop`
limpia. No importa internos del runtime.

El manifest generado incluye una sección `[controller]` con `layout = "motion"`,
`skin = "tokyo-night"`, etiquetas y hint. Ajustala al gesto principal del juego:
ver [`input-and-controls.md`](input-and-controls.md#perfil-controller). También
incluye `[art] motif = "auto"`; cambialo si querés un prop específico del
diorama.

La implementación vive en `src/toxinator/dev/projects.py`; los tests unitarios
en `tests/unit/test_projects.py` y `tests/unit/test_cli.py` cubren el esqueleto,
la validación del id, el symlink, `--force` y la idempotencia.

## Carga del launcher

`src/toxinator/dev/launcher.py` arma el catálogo con `load_catalog()` y lo
extiende con `external_entries()`. Cada entrada externa es un `GameEntry` con
`installed=True` y `factory` apuntando a `create_game`; el launcher las muestra
en **Tus juegos** y en el **Catálogo**, y las instancia igual que un built-in.

## Carga de `toxinator play`

`src/toxinator/dev/play.py::load_game`:

1. Busca un juego built-in con `find_game`.
2. Si no existe, busca un externo con `find_external_game`.
3. Si el built-in existe pero no está instalado, error explícito.
4. Si no hay ninguno, `juego desconocido`.

Esto mantiene `toxinator play maldito-pino` igual y permite
`toxinator play mi-juego` sin tocar el repo.

## Juego built-in (si va al repo)

Solo para el juego de ejemplo oficial:

1. `src/toxinator/core/games.py`:
   - `_<juego>()` lee `files("<module>").joinpath("manifest.toml")`.
   - `GameEntry` con metadata de catálogo.
   - rama en `GameEntry.instantiate()`.
   - alta en `load_catalog()`.
2. `src/toxinator/dev/play.py`: `find_game()` ya cubre built-in; no agregues una
   rama específica si el juego es externo.
3. `pyproject.toml` raíz:
   - `[tool.uv.workspace].members`
   - `[tool.pytest.ini_options].testpaths`
   - `[tool.mypy].files`
4. `tests/unit/test_catalog.py`: actualizá la lista hardcodeada de ids.
5. `uv sync --all-packages`.

## Tests

```bash
cd /home/ska/Projects/toxinator
uv run pytest
uv run ruff check src tests games
uv run mypy
```

- Tests unitarios: lógica pura, sin Panda3D.
- Tests de integración: `ShowBase` headless/offscreen.
- Tests de un juego externo: no están en `testpaths`; corrélos aparte con su
  propio `PYTHONPATH`/venv. El test del cargador externo está en
  `tests/unit/test_external_games.py`.
- `--demo` evita necesitar celular.
- `--offscreen` evita necesitar display/GPU.

## Correr un juego externo

```bash
uv run toxinator play mi-juego
uv run toxinator play mi-juego --demo
uv run toxinator play mi-juego --cloudflare   # HTTPS válido sin CA
uv run toxinator play mi-juego --demo --offscreen \
  --screenshot /tmp/mi-juego.png --screenshot-after 3 --seconds 5
```

`--https` es aparte: sirve para sensores/cámara/PWA; el loader y el contrato no
cambian. `--cloudflare` levanta un Quick Tunnel HTTPS con certificado válido y
evita instalar una CA en el teléfono; requiere `cloudflared` e internet.

## Checklist

- [ ] `manifest.toml` dentro de `src/<module>/`.
- [ ] `create_game(manifest)` en `__init__.py`.
- [ ] Módulo único y paquete importable.
- [ ] Solo `toxinator.api` del runtime.
- [ ] `start/update/stop` y limpieza.
- [ ] Diseño motion-first con touch + A como fallback.
- [ ] Perfil `[controller]` (layout/skin/action/hint) declarado.
- [ ] Feedback opcional probado (vibración/tono) sin bloquear.
- [ ] B no se usa.
- [ ] Probado `--demo` y `--offscreen`.
- [ ] README del juego externo actualizado.
- [ ] Skill actualizado si cambió el loader/contrato.
