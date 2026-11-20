"""Create and install external game projects."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from toxinator.api.game import API_VERSION, load_manifest
from toxinator.core.external_games import games_dir

GAME_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
SKILL_NAME = "toxinator-game-dev"

MANIFEST_TEMPLATE = """\
id = "{game_id}"
name = "{title}"
version = "0.1.0"
requires_api = "{api_version}"
description = "{description}"
locales = ["es"]
default_locale = "es"
players = [1, 4]
modes = ["partida"]

[controller]
layout = "motion"
skin = "toxinator"
orientation = "auto"
hint = "Incliná el teléfono o usá el stick"

[controller.labels]
cross = "Acción"
circle = "Volver"

[art]
motif = "auto"
"""

INIT_TEMPLATE = """\
from __future__ import annotations

from toxinator.api import Game, GameManifest

from .game import {class_name}


def create_game(manifest: GameManifest) -> Game:
    return {class_name}(manifest)
"""

GAME_TEMPLATE = '''\
"""Minimal game: shows a message and reacts to cross."""

from __future__ import annotations

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, Vec4

from toxinator.api import GameContext, GameManifest


class {class_name}:
    """Smallest useful game for the Toxinator console."""

    def __init__(self, manifest: GameManifest) -> None:
        self.manifest = manifest
        self.ctx: GameContext | None = None
        self.root = None
        self.ui_root = None
        self.label: OnscreenText | None = None
        self.pressed = False

    def start(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self.root = ctx.scene.attach_new_node("{game_id}")
        self.ui_root = ctx.ui.attach_new_node("{game_id}-ui")
        self.label = OnscreenText(
            text={label_text},
            parent=self.ui_root,
            pos=(0.0, 0.0),
            scale=0.08,
            fg=Vec4(1.0, 1.0, 1.0, 1.0),
            align=TextNode.ACenter,
            mayChange=True,
            shadow=Vec4(0.0, 0.0, 0.0, 0.6),
        )

    def update(self, dt: float) -> None:
        if self.ctx is None or self.label is None:
            return
        frame = self.ctx.input_state.primary_frame()
        pressed = frame is not None and frame.button("cross")
        if pressed and not self.pressed:
            self.label.setText("X / OK")
            self.ctx.phone.vibrate([18])
            self.ctx.phone.tone(880, 60, volume=0.25)
        elif not pressed and self.pressed:
            self.label.setText({label_text})
        self.pressed = pressed

    def stop(self) -> None:
        if self.ui_root is not None:
            self.ui_root.remove_node()
            self.ui_root = None
        if self.root is not None:
            self.root.remove_node()
            self.root = None
        self.label = None
        self.ctx = None
'''

PYPROJECT_TEMPLATE = """\
[project]
name = "toxinator-game-{game_id}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.14,<3.15"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{module}"]
"""

README_TEMPLATE = """\
# {title}

Juego externo para la consola Toxinator (id `{game_id}`).

```text
{game_id}/
├── src/
│   └── {module}/
│       ├── __init__.py      # create_game(manifest)
│       ├── manifest.toml
│       └── game.py
└── pyproject.toml           # opcional
```

## Instalar en la consola

```bash
toxinator install .
toxinator play {game_id}
```

El instalador deja un symlink en el directorio de juegos externos
(`TOXINATOR_GAMES_DIR` o `~/Projects/toxinator-games`) y el launcher lo muestra
en la **biblioteca** al iniciar.

## Reglas

- Importá solo `toxinator.api` del runtime.
- No crees `ShowBase` ni ventanas; usá `ctx.scene` y `ctx.ui`.
- Leé el input desde `ctx.input_state.primary_frame()`; `circle` está reservado
  para volver.
- Jugable con **stick + touch + ×**; los sensores solo funcionan con HTTPS.
- Limpiá nodos y recursos en `stop`.

## Skill de desarrollo

Este directorio incluye `.opencode/skills/toxinator-game-dev/`, la guía para
desarrollar juegos para Toxinator: contrato, manifest, input del celular,
instalación y tests. Es una copia del skill del repo de la consola; si la
plataforma cambia, volvé a crearlo o actualizá esa carpeta a mano.
"""


class GameProjectError(RuntimeError):
    """An external game project cannot be created or installed."""


@dataclass(frozen=True, slots=True)
class GameProject:
    """A scaffolded external game on disk."""

    game_id: str
    module: str
    root: Path


def game_id_to_module(game_id: str) -> str:
    """Return the Python module name for a game id."""
    return game_id.replace("-", "_")


def module_to_class(module: str) -> str:
    """Return a PascalCase class name for a module name."""
    return "".join(part[:1].upper() + part[1:] for part in module.split("_") if part)


def default_title(game_id: str) -> str:
    """Return a human title derived from the game id."""
    return " ".join(part.capitalize() for part in re.split(r"[-_]+", game_id) if part)


def _validate_game_id(game_id: str) -> None:
    if not GAME_ID_RE.fullmatch(game_id):
        raise GameProjectError(
            f"id de juego inválido: {game_id!r} "
            "(usá minúsculas, números, '-' o '_', y empezá con una letra)"
        )


def _toml_string(value: str) -> str:
    """Escape a value for a double-quoted TOML string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _link_name(game_id: str) -> str:
    """Return a safe single-component directory name for ``game_id``."""
    name = Path(game_id).name
    if name != game_id or name in {"", ".", ".."} or name.startswith((".", "_")):
        raise GameProjectError(f"id de juego inválido para instalar: {game_id!r}")
    return name


def _skill_source() -> Path:
    """Locate the local game development skill shipped with the console."""
    for base in Path(__file__).resolve().parents:
        candidate = base / ".opencode" / "skills" / SKILL_NAME
        if candidate.joinpath("SKILL.md").is_file():
            return candidate
    raise GameProjectError(
        f"no encontré el skill {SKILL_NAME} "
        f"(.opencode/skills/{SKILL_NAME}) junto a la instalación de toxinator"
    )


def create_game_project(
    game_id: str,
    parent: Path,
    *,
    title: str | None = None,
) -> GameProject:
    """Create the skeleton of an external game under ``parent/<game_id>``.

    ``parent`` must exist. The target directory may be missing or empty; an
    existing directory with content is never overwritten.
    """
    _validate_game_id(game_id)
    if not parent.is_dir():
        raise GameProjectError(f"el directorio destino no existe: {parent}")

    root = parent / game_id
    if root.exists():
        if not root.is_dir():
            raise GameProjectError(f"ya existe un archivo en {root}")
        if any(root.iterdir()):
            raise GameProjectError(f"el directorio no está vacío: {root}")

    module = game_id_to_module(game_id)
    class_name = module_to_class(module)
    display_title = " ".join(title.split()) if title else default_title(game_id)
    description = f"Juego externo de Toxinator ({display_title})."
    label_text = repr(f"{display_title.upper()}\nX / ACCIÓN")
    manifest_title = _toml_string(display_title)
    manifest_description = _toml_string(description)
    skill_source = _skill_source()
    existed = root.exists()

    package = root / "src" / module
    try:
        package.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            skill_source,
            root / ".opencode" / "skills" / SKILL_NAME,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        package.joinpath("manifest.toml").write_text(
            MANIFEST_TEMPLATE.format(
                game_id=game_id,
                title=manifest_title,
                api_version=API_VERSION,
                description=manifest_description,
            ),
            encoding="utf-8",
        )
        package.joinpath("__init__.py").write_text(
            INIT_TEMPLATE.format(class_name=class_name),
            encoding="utf-8",
        )
        package.joinpath("game.py").write_text(
            GAME_TEMPLATE.format(
                class_name=class_name,
                game_id=game_id,
                label_text=label_text,
            ),
            encoding="utf-8",
        )
        root.joinpath("pyproject.toml").write_text(
            PYPROJECT_TEMPLATE.format(
                game_id=game_id,
                module=module,
                description=manifest_description,
            ),
            encoding="utf-8",
        )
        root.joinpath("README.md").write_text(
            README_TEMPLATE.format(
                game_id=game_id,
                module=module,
                title=display_title,
            ),
            encoding="utf-8",
        )
    except OSError:
        if not existed:
            shutil.rmtree(root, ignore_errors=True)
        raise
    return GameProject(game_id=game_id, module=module, root=root)


def _find_manifest(directory: Path) -> Path:
    matches = sorted(directory.glob("src/*/manifest.toml"))
    if not matches:
        raise GameProjectError(
            f"no encontré un juego en {directory} (falta src/<módulo>/manifest.toml)"
        )
    if len(matches) > 1:
        found = ", ".join(str(path) for path in matches)
        raise GameProjectError(f"hay más de un manifest en {directory}: {found}")
    return matches[0]


def install_game_project(
    directory: Path,
    *,
    games_root: Path | None = None,
    force: bool = False,
) -> Path:
    """Install a game by linking it into the external games directory.

    Returns the path of the link (or of the existing directory when the game
    already lives in the games directory). Existing content is never removed
    unless it is a symlink and ``force`` is true.
    """
    source = directory.expanduser().resolve()
    if not source.is_dir():
        raise GameProjectError(f"el directorio del juego no existe: {directory}")

    manifest_path = _find_manifest(source)
    manifest = load_manifest(manifest_path)
    game_root = manifest_path.parent.parent.parent

    root = (games_root or games_dir()).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    link = root / _link_name(manifest.id)
    target = game_root.resolve()

    if link.is_symlink() or link.exists():
        if link.resolve() == target:
            return link
        if not force:
            raise GameProjectError(f"ya existe {link}; usá --force para reemplazar el symlink")
        if not link.is_symlink():
            raise GameProjectError(f"{link} no es un symlink; no lo reemplazo")
        link.unlink()

    relative = os.path.relpath(target, start=link.parent)
    link.symlink_to(relative, target_is_directory=True)
    return link
