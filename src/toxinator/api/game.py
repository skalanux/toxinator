"""Game contract: manifest, context and lifecycle."""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from toxinator.api.input import CANONICAL_BUTTONS, InputState
from toxinator.api.phone import PhoneService

API_VERSION = "0.4"

CONTROLLER_LAYOUTS = ("default", "motion", "touch")
CONTROLLER_SKINS = ("toxinator",)
CONTROLLER_ORIENTATIONS = ("auto", "portrait", "landscape")
PANEL_FITS = ("contain", "cover", "stretch")

GESTURES: tuple[str, ...] = (
    "tilt",
    "steer",
    "aim",
    "flick",
    "swing",
    "twist",
    "shake",
    "flip",
)

GESTURE_KINDS: dict[str, str] = {
    "tilt": "posture",
    "steer": "posture",
    "aim": "pointer",
    "flick": "event",
    "swing": "event",
    "twist": "event",
    "shake": "event",
    "flip": "event",
}

GESTURE_DEFAULT_LABELS: dict[str, str] = {
    "tilt": "Inclinar",
    "steer": "Doblar",
    "aim": "Apuntar",
    "flick": "Sacudir",
    "swing": "Golpear",
    "twist": "Girar",
    "shake": "Agitar",
    "flip": "Voltear",
}
DEFAULT_CONTROLLER_LAYOUT = "default"
DEFAULT_CONTROLLER_SKIN = "toxinator"
DEFAULT_CONTROLLER_ORIENTATION = "auto"
DEFAULT_CONTROLLER_ACTION = "Acción"
DEFAULT_CONTROLLER_BACK = "Volver"
DEFAULT_PANEL_FIT = "contain"
ART_MOTIFS = ("auto", "pin", "flag", "paddle", "pong", "star", "heart", "coin", "cube")
DEFAULT_ART_MOTIF = "auto"


@dataclass(frozen=True, slots=True)
class ControllerPanel:
    """Static image a game can show on the phone (map, reference, legend)."""

    title: str
    image: str
    fit: str = DEFAULT_PANEL_FIT

    def as_dict(self) -> dict[str, str]:
        return {"title": self.title, "image": self.image, "fit": self.fit}


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
    controller_orientation: str = DEFAULT_CONTROLLER_ORIENTATION
    controller_labels: Mapping[str, str] = field(default_factory=dict)
    controller_panel: ControllerPanel | None = None
    controller_camera: bool = False
    controller_gestures: tuple[str, ...] = ()
    controller_gesture_labels: Mapping[str, str] = field(default_factory=dict)
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


def _bounded_text(value: Any, limit: int, default: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    return (text or default)[:limit]


def _asset_reference(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    path = value.strip()
    if not path or len(path) > 200:
        return None
    if "://" in path or path.startswith("/") or "\\" in path:
        return None
    if any(part == ".." for part in path.split("/")):
        return None
    return path


def _parse_labels(controller: Mapping[str, Any], action: str, back: str) -> dict[str, str]:
    raw = controller.get("labels", {})
    labels = {"cross": action, "circle": back}
    if not isinstance(raw, dict):
        return labels
    for key, value in raw.items():
        name = str(key).lower()
        if name not in CANONICAL_BUTTONS or not isinstance(value, str):
            continue
        labels[name] = value.strip()[:24]
    return labels


def _parse_panel(controller: Mapping[str, Any]) -> ControllerPanel | None:
    raw = controller.get("panel", {})
    if not isinstance(raw, dict):
        return None
    image = _asset_reference(raw.get("image"))
    if image is None:
        return None
    title = _bounded_text(raw.get("title"), 40)
    fit = str(raw.get("fit", DEFAULT_PANEL_FIT))
    if fit not in PANEL_FITS:
        fit = DEFAULT_PANEL_FIT
    return ControllerPanel(title=title, image=image, fit=fit)


def _parse_gestures(controller: Mapping[str, Any]) -> tuple[str, ...]:
    raw = controller.get("gestures", [])
    names: list[str] = []
    if not isinstance(raw, list):
        return ()
    for item in raw:
        name = str(item).strip().lower()
        if name in GESTURES and name not in names:
            names.append(name)
    return tuple(names[:8])


def _parse_gesture_labels(controller: Mapping[str, Any]) -> dict[str, str]:
    raw = controller.get("gesture_labels", {})
    labels: dict[str, str] = {}
    if not isinstance(raw, dict):
        return labels
    for key, value in raw.items():
        name = str(key).strip().lower()
        if name in GESTURES and isinstance(value, str):
            labels[name] = value.strip()[:24]
    return labels


def gesture_entries(
    gestures: Sequence[str], labels: Mapping[str, str]
) -> list[dict[str, str]]:
    """Shape the declared gestures for the phone profile."""
    return [
        {
            "name": name,
            "label": labels.get(name, GESTURE_DEFAULT_LABELS.get(name, name)),
            "kind": GESTURE_KINDS.get(name, "event"),
        }
        for name in gestures
    ]


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
    orientation = str(controller.get("orientation", DEFAULT_CONTROLLER_ORIENTATION))
    if orientation not in CONTROLLER_ORIENTATIONS:
        orientation = DEFAULT_CONTROLLER_ORIENTATION
    action = str(controller.get("action", DEFAULT_CONTROLLER_ACTION))[:24]
    back = str(controller.get("back", DEFAULT_CONTROLLER_BACK))[:24]
    hint = str(controller.get("hint", ""))[:80]
    labels = _parse_labels(controller, action, back)
    panel = _parse_panel(controller)
    camera = controller.get("camera", False) is True
    gestures = _parse_gestures(controller)
    gesture_labels = _parse_gesture_labels(controller)

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
        controller_orientation=orientation,
        controller_labels=labels,
        controller_panel=panel,
        controller_camera=camera,
        controller_gestures=gestures,
        controller_gesture_labels=gesture_labels,
        art_motif=art_motif,
    )
