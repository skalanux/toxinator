"""``toxinator play``: load a game, open the console and connect the phone."""

from __future__ import annotations

import logging
from pathlib import Path

from panda3d.core import loadPrcFileData

from toxinator.api.game import Game, GameManifest
from toxinator.core.external_games import find_external_game
from toxinator.core.games import find_game
from toxinator.dev.announce import announce_phone
from toxinator.dev.game_app import GameApp
from toxinator.dev.session import start_phone_session

logger = logging.getLogger(__name__)


def load_game(game_id: str) -> tuple[GameManifest, Game]:
    try:
        entry = find_game(game_id)
    except RuntimeError:
        entry = None
    if entry is not None:
        if not entry.installed or entry.manifest is None:
            raise RuntimeError(f"{entry.title} todavía no está instalado")
        return entry.manifest, entry.instantiate()

    external = find_external_game(game_id)
    if external is not None:
        return external.manifest, external.instantiate()
    raise RuntimeError(f"juego desconocido: {game_id}")


def run_play(
    *,
    game_id: str = "maldito-pino",
    host: str | None = None,
    port: int = 8443,
    token: str | None = None,
    demo: bool = False,
    seconds: float | None = None,
    offscreen: bool = False,
    screenshot: Path | None = None,
    screenshot_after: float = 3.0,
    https: bool = False,
    cert: Path | None = None,
    key: Path | None = None,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    manifest, game = load_game(game_id)
    session = start_phone_session(
        host=host, port=port, token=token, demo=demo, https=https, cert=cert, key=key
    )
    session.set_mode("game")
    if session.host.startswith("127."):
        print(
            "Aviso: el host es loopback; el celular no va a poder conectarse. "
            "Pasá --host con la IP de la LAN.",
            flush=True,
        )

    try:
        announce_phone(
            session,
            title=f"TOXINATOR · {manifest.name}",
            demo=demo,
            extra=f"Juego: {manifest.id} v{manifest.version}",
        )

        window_type = "offscreen" if offscreen or screenshot is not None else "onscreen"
        sync_video = "true" if window_type == "onscreen" else "false"
        loadPrcFileData(
            "",
            "win-size 1280 720\n"
            "audio-library-name null\n"
            f"sync-video {sync_video}\n"
            "notify-level-display error\n"
            "notify-level-glgsg error\n",
        )
        if screenshot is not None:
            screenshot.parent.mkdir(parents=True, exist_ok=True)

        app = GameApp(
            session.hub,
            game,
            window_type=window_type,
            screenshot=screenshot,
            screenshot_after=screenshot_after,
            seconds=seconds,
        )
        app.run()
    finally:
        session.stop()
