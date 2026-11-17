"""Game catalog for the launcher and the direct ``play`` command."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

from toxinator.api.game import Game, GameManifest, load_manifest


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
    manifest: GameManifest | None = None

    def instantiate(self) -> Game:
        if not self.installed:
            raise RuntimeError(f"{self.title} todavía no está instalado")
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
                    "desafío de la liga."
                ),
                rank="C",
                event="02",
                record="—",
                players=(1, 4),
                modes=("carrera",),
                installed=False,
                accent="gold",
            ),
            GameEntry(
                id="tenis",
                title="Tenis de vereda",
                subtitle="PALETA Y CALLE",
                description=(
                    "Pelota, paleta y cordón. Otro clásico de la liga que todavía está "
                    "calentando."
                ),
                rank="C",
                event="03",
                record="—",
                players=(1, 4),
                modes=("partido",),
                installed=False,
                accent="jade",
            ),
        ]
    )
    return entries


def find_game(game_id: str) -> GameEntry:
    for entry in load_catalog():
        if entry.id == game_id:
            return entry
    raise RuntimeError(f"juego desconocido: {game_id}")
