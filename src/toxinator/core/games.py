"""Game catalog for the launcher and the direct ``play`` command."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from toxinator.api.game import ControllerPanel, Game, GameManifest, load_manifest


@dataclass(frozen=True, slots=True)
class GameEntry:
    id: str
    title: str
    subtitle: str
    description: str
    rank: str
    event: str
    record: str
    players: tuple[int, int]
    modes: tuple[str, ...]
    installed: bool
    accent: str
    controller_layout: str = "default"
    controller_skin: str = "toxinator"
    controller_action: str = "Acción"
    controller_back: str = "Volver"
    controller_hint: str = ""
    controller_orientation: str = "auto"
    controller_labels: Mapping[str, str] = field(default_factory=dict)
    controller_panel: ControllerPanel | None = None
    controller_camera: bool = False
    controller_gestures: tuple[str, ...] = ()
    controller_gesture_labels: Mapping[str, str] = field(default_factory=dict)
    assets_root: Path | None = None
    art_motif: str = "auto"
    manifest: GameManifest | None = None
    factory: Callable[[GameManifest], Game] | None = None

    def instantiate(self) -> Game:
        if not self.installed:
            raise RuntimeError(f"{self.title} todavía no está instalado")
        if self.factory is not None:
            if self.manifest is None:
                raise RuntimeError(f"{self.title} no tiene manifest")
            return self.factory(self.manifest)
        if self.id == "maldito-pino":
            from maldito_pino.game import MalditoPinoGame

            assert self.manifest is not None
            return MalditoPinoGame(self.manifest)
        raise RuntimeError(f"no sé cómo cargar {self.id}")


def _maldito_pino() -> GameEntry | None:
    try:
        manifest_text = (
            files("maldito_pino").joinpath("manifest.toml").read_text(encoding="utf-8")
        )
    except (ModuleNotFoundError, FileNotFoundError):
        return None
    manifest = load_manifest(manifest_text)
    return GameEntry(
        id=manifest.id,
        title="Maldito Pino",
        subtitle="HIJO DE PU** · BOLOS DE BARRIO",
        description=(
            "Diez pinos con actitud, una bola y una pista. Apuntá con el celular, "
            "inclinalo para dar efecto y soltá la potencia en el momento justo."
        ),
        rank="A",
        event="01",
        record="—",
        players=manifest.players,
        modes=manifest.modes,
        installed=True,
        accent="crimson",
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
        assets_root=Path(str(files("maldito_pino"))).resolve(),
        art_motif=manifest.art_motif,
        manifest=manifest,
    )


def load_catalog() -> list[GameEntry]:
    entries: list[GameEntry] = []
    maldito = _maldito_pino()
    if maldito is not None:
        entries.append(maldito)
    entries.extend(
        [
            GameEntry(
                id="kart",
                title="Kart de barrio",
                subtitle="CARRERAS",
                description=(
                    "Cuatro karts, una cuadra y ninguna regla de tránsito. El próximo "
                    "juego de la consola."
                ),
                rank="C",
                event="02",
                record="—",
                players=(1, 4),
                modes=("carrera",),
                installed=False,
                accent="gold",
                controller_layout="motion",
                controller_skin="toxinator",
                controller_action="Acelerar",
                controller_back="Volver",
                controller_hint="Incliná para doblar",
                controller_labels={"cross": "Acelerar", "circle": "Volver"},
                art_motif="flag",
            ),
            GameEntry(
                id="tenis",
                title="Tenis de vereda",
                subtitle="PALETA Y CALLE",
                description=(
                    "Pelota, paleta y cordón. Otro clásico que todavía está "
                    "calentando."
                ),
                rank="C",
                event="03",
                record="—",
                players=(1, 4),
                modes=("partido",),
                installed=False,
                accent="jade",
                controller_layout="motion",
                controller_skin="toxinator",
                controller_action="Golpear",
                controller_back="Volver",
                controller_hint="Incliná para dirigir",
                controller_labels={"cross": "Golpear", "circle": "Volver"},
                art_motif="paddle",
            ),
        ]
    )
    return entries


def find_game(game_id: str) -> GameEntry:
    for entry in load_catalog():
        if entry.id == game_id:
            return entry
    raise RuntimeError(f"juego desconocido: {game_id}")
