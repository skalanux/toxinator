"""``toxinator play``: load a game, open the console and connect the phone."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from panda3d.core import loadPrcFileData

from toxinator.api.game import Game, GameManifest
from toxinator.core.external_games import find_external_game
from toxinator.core.games import find_game
from toxinator.dev.announce import announce_phone
from toxinator.dev.fps import FpsOverlay
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


def game_assets_root(game: Game) -> Path | None:
    """Best-effort package directory for a game's static assets."""
    module = sys.modules.get(type(game).__module__)
    source = getattr(module, "__file__", None)
    if not source:
        return None
    return Path(source).resolve().parent


def controller_profile(
    manifest: GameManifest, *, game: str | None = None
) -> dict[str, Any]:
    labels = dict(manifest.controller_labels)
    panel = (
        manifest.controller_panel.as_dict()
        if manifest.controller_panel is not None
        else None
    )
    return {
        "layout": manifest.controller_layout,
        "skin": manifest.controller_skin,
        "orientation": manifest.controller_orientation,
        "buttons": ["cross", "circle", "square", "triangle", "options", "l1", "r1"],
        "labels": labels,
        "action": labels.get("cross", manifest.controller_action),
        "back": labels.get("circle", manifest.controller_back),
        "hint": manifest.controller_hint,
        "camera": manifest.controller_camera,
        "panel": panel,
        "game": game if game is not None else manifest.name,
    }


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
    keyboard: bool = True,
    keyboard_slot: int = 4,
    https: bool = False,
    cert: Path | None = None,
    key: Path | None = None,
    cloudflare: bool = False,
    show_fps: bool = False,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    manifest, game = load_game(game_id)
    session = start_phone_session(
        host=host,
        port=port,
        token=token,
        demo=demo,
        keyboard=keyboard,
        keyboard_slot=keyboard_slot,
        https=https,
        cert=cert,
        key=key,
        cloudflare=cloudflare,
    )
    session.set_mode("game")
    session.set_game_assets(manifest.id, game_assets_root(game))
    session.set_controller(controller_profile(manifest))
    if session.tunnel is None and session.host.startswith("127."):
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
            phone=session.feedback,
            keyboard=session.keyboard,
        )
        if show_fps:
            FpsOverlay(app)
        app.run()
    finally:
        session.stop()
