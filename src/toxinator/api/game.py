"""Game contract: manifest, context and lifecycle."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from toxinator.api.input import InputState

API_VERSION = "0.1"


@dataclass(frozen=True, slots=True)
class GameManifest:
    id: str
    name: str
    version: str
    requires_api: str
    description: str = ""
    locales: tuple[str, ...] = ("es",)
    default_locale: str = "es"
    players: tuple[int, int] = (1, 4)
    modes: tuple[str, ...] = ("partida",)


@dataclass
class GameContext:
    """Everything a game gets from the console.

    The console owns the ShowBase; the game gets a scene root, a UI root and
    the latest input snapshot. It must not create windows or a ShowBase.
    """

    base: Any
    scene: Any
    ui: Any
    input_state: InputState
    locale: str = "es"
    request_exit: Callable[[], None] | None = None


class Game(Protocol):
    manifest: GameManifest

    def start(self, ctx: GameContext) -> None: ...

    def update(self, dt: float) -> None: ...

    def stop(self) -> None: ...


def load_manifest(source: str | Path) -> GameManifest:
    """Parse a TOML manifest from text or a path."""
    if isinstance(source, Path):
        data = tomllib.loads(source.read_text(encoding="utf-8"))
    else:
        data = tomllib.loads(source)

    players = tuple(int(value) for value in data.get("players", [1, 4]))
    if len(players) != 2:
        players = (1, 4)

    return GameManifest(
        id=str(data["id"]),
        name=str(data["name"]),
        version=str(data.get("version", "0.0.0")),
        requires_api=str(data.get("requires_api", API_VERSION)),
        description=str(data.get("description", "")),
        locales=tuple(str(value) for value in data.get("locales", ["es"])),
        default_locale=str(data.get("default_locale", "es")),
        players=(players[0], players[1]),
        modes=tuple(str(value) for value in data.get("modes", ["partida"])),
    )
