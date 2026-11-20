"""Game contract: manifest, context and lifecycle."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from toxinator.api.input import InputState
from toxinator.api.phone import PhoneService

API_VERSION = "0.2"

CONTROLLER_LAYOUTS = ("default", "motion", "touch")
CONTROLLER_SKINS = ("tokyo-night", "tokyo-storm", "tokyo-moon", "tokyo-mint")
DEFAULT_CONTROLLER_LAYOUT = "default"
DEFAULT_CONTROLLER_SKIN = "tokyo-night"
DEFAULT_CONTROLLER_ACTION = "Acción"
DEFAULT_CONTROLLER_BACK = "Volver"
ART_MOTIFS = ("auto", "pin", "flag", "paddle", "pong", "star", "heart", "coin", "cube")
DEFAULT_ART_MOTIF = "auto"


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
    controller_layout: str = DEFAULT_CONTROLLER_LAYOUT
    controller_skin: str = DEFAULT_CONTROLLER_SKIN
    controller_action: str = DEFAULT_CONTROLLER_ACTION
    controller_back: str = DEFAULT_CONTROLLER_BACK
    controller_hint: str = ""
    art_motif: str = DEFAULT_ART_MOTIF


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
    phone: PhoneService
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

    controller = data.get("controller", {})
    if not isinstance(controller, dict):
        controller = {}
    layout = str(controller.get("layout", DEFAULT_CONTROLLER_LAYOUT))
    if layout not in CONTROLLER_LAYOUTS:
        layout = DEFAULT_CONTROLLER_LAYOUT
    skin = str(controller.get("skin", DEFAULT_CONTROLLER_SKIN))
    if skin not in CONTROLLER_SKINS:
        skin = DEFAULT_CONTROLLER_SKIN
    action = str(controller.get("action", DEFAULT_CONTROLLER_ACTION))[:24]
    back = str(controller.get("back", DEFAULT_CONTROLLER_BACK))[:24]
    hint = str(controller.get("hint", ""))[:80]

    art = data.get("art", {})
    if not isinstance(art, dict):
        art = {}
    art_motif = str(art.get("motif", DEFAULT_ART_MOTIF))
    if art_motif not in ART_MOTIFS:
        art_motif = DEFAULT_ART_MOTIF

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
        controller_layout=layout,
        controller_skin=skin,
        controller_action=action,
        controller_back=back,
        controller_hint=hint,
        art_motif=art_motif,
    )
