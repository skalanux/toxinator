"""Discover games from a directory outside the platform repository."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import cast

from toxinator.api.game import Game, GameManifest, load_manifest
from toxinator.core.games import GameEntry

logger = logging.getLogger(__name__)

GAMES_DIR_ENV = "TOXINATOR_GAMES_DIR"


@dataclass(frozen=True, slots=True)
class ExternalGame:
    """A game package loaded from the external games directory."""

    manifest: GameManifest
    factory: Callable[[GameManifest], Game]
    path: Path

    def instantiate(self) -> Game:
        return self.factory(self.manifest)


def games_dir() -> Path:
    """Return the external games directory.

    ``TOXINATOR_GAMES_DIR`` wins. Otherwise prefer the sibling ``Projects``
    directory on this workstation, then the home default.
    """
    override = os.environ.get(GAMES_DIR_ENV)
    if override:
        return Path(override).expanduser()
    projects = Path.home() / "Projects" / "toxinator-games"
    if projects.is_dir():
        return projects
    return Path.home() / "toxinator-games"


def _is_hidden(relative: Path) -> bool:
    return any(part.startswith((".", "_")) for part in relative.parts)


def _load_module(directory: Path, module_name: str) -> ModuleType | None:
    source = str(directory)
    if source not in sys.path:
        sys.path.insert(0, source)
    try:
        return import_module(module_name)
    except Exception:
        logger.exception("no pude importar el juego externo %s", module_name)
        return None


def discover_external_games(directory: Path | None = None) -> list[ExternalGame]:
    """Scan ``directory`` for game packages and return valid factories.

    Expected layout, one package per game::

        <games-dir>/<game>/src/<module>/manifest.toml
        <games-dir>/<game>/src/<module>/__init__.py   # create_game(manifest)

    Invalid packages are logged and skipped so a broken external game does not
    take down the console.
    """
    root = directory or games_dir()
    if not root.is_dir():
        return []

    games: list[ExternalGame] = []
    seen: set[str] = set()
    for manifest_path in sorted(root.glob("*/src/*/manifest.toml")):
        relative = manifest_path.relative_to(root)
        if _is_hidden(relative):
            continue
        package_dir = manifest_path.parent
        source_dir = package_dir.parent
        module_name = package_dir.name

        try:
            manifest = load_manifest(manifest_path)
        except Exception:
            logger.exception("manifest externo inválido: %s", manifest_path)
            continue
        if manifest.id in seen:
            logger.warning("juego externo duplicado, ignorado: %s", manifest.id)
            continue

        module = _load_module(source_dir, module_name)
        if module is None:
            continue
        factory = getattr(module, "create_game", None)
        if not callable(factory):
            logger.warning(
                "el juego externo %s no expone create_game(manifest)",
                module_name,
            )
            continue

        games.append(
            ExternalGame(
                manifest=manifest,
                factory=cast(Callable[[GameManifest], Game], factory),
                path=manifest_path,
            )
        )
        seen.add(manifest.id)
    return games


def find_external_game(
    game_id: str, directory: Path | None = None
) -> ExternalGame | None:
    """Find one external game by manifest id."""
    for game in discover_external_games(directory):
        if game.manifest.id == game_id:
            return game
    return None


def as_game_entry(game: ExternalGame) -> GameEntry:
    """Adapt an external game to the launcher catalog shape."""
    manifest = game.manifest
    return GameEntry(
        id=manifest.id,
        title=manifest.name,
        subtitle="JUEGO EXTERNO",
        description=manifest.description or "Juego de la biblioteca externa.",
        rank="EX",
        event="EX",
        record="—",
        players=manifest.players,
        modes=manifest.modes,
        installed=True,
        accent="gold",
        controller_layout=manifest.controller_layout,
        controller_skin=manifest.controller_skin,
        controller_action=manifest.controller_action,
        controller_back=manifest.controller_back,
        controller_hint=manifest.controller_hint,
        controller_orientation=manifest.controller_orientation,
        controller_labels=manifest.controller_labels,
        controller_panel=manifest.controller_panel,
        controller_camera=manifest.controller_camera,
        controller_gestures=manifest.controller_gestures,
        controller_gesture_labels=manifest.controller_gesture_labels,
        assets_root=game.path.parent,
        art_motif=manifest.art_motif,
        manifest=manifest,
        factory=game.factory,
    )


def external_entries(directory: Path | None = None) -> list[GameEntry]:
    """Return external games ready to be listed by the launcher."""
    return [as_game_entry(game) for game in discover_external_games(directory)]
