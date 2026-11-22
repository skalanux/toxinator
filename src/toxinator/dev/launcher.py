"""``toxinator launcher``: the Toxinator console home and game launch."""

from __future__ import annotations

import logging
from pathlib import Path

from panda3d.core import loadPrcFileData

from toxinator.core.external_games import external_entries
from toxinator.core.games import load_catalog
from toxinator.dev.announce import announce_phone
from toxinator.dev.fps import FpsOverlay
from toxinator.dev.session import start_phone_session
from toxinator.launcher.app import ConsoleApp

logger = logging.getLogger(__name__)


def run_launcher(
    *,
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

    catalog = load_catalog()
    external = external_entries()
    if external:
        logger.info("juegos externos encontrados: %s", ", ".join(e.id for e in external))
    catalog.extend(external)
    session = start_phone_session(
        host=host,
        port=port,
        token=token,
        demo=demo,
        demo_buttons=False,
        keyboard=keyboard,
        keyboard_slot=keyboard_slot,
        https=https,
        cert=cert,
        key=key,
        cloudflare=cloudflare,
    )
    if session.tunnel is None and session.host.startswith("127."):
        print(
            "Aviso: el host es loopback; el celular no va a poder conectarse. "
            "Pasá --host con la IP de la LAN.",
            flush=True,
        )

    try:
        announce_phone(
            session,
            title="TOXINATOR",
            demo=demo,
            extra="Elegí un juego con las flechas y Enter.",
        )

        window_type = "offscreen" if offscreen or screenshot is not None else "onscreen"
        sync_video = "true" if window_type == "onscreen" else "false"
        loadPrcFileData(
            "",
            "win-size 1280 720\n"
            f"sync-video {sync_video}\n"
            "notify-level-display error\n"
            "notify-level-glgsg error\n",
        )
        if screenshot is not None:
            screenshot.parent.mkdir(parents=True, exist_ok=True)

        app = ConsoleApp(
            session.hub,
            catalog,
            session.url,
            window_type=window_type,
            screenshot=screenshot,
            screenshot_after=screenshot_after,
            seconds=seconds,
            set_mode=session.set_mode,
            set_controller=session.set_controller,
            set_game_assets=session.set_game_assets,
            phone=session.feedback,
            keyboard=session.keyboard,
        )
        if show_fps:
            FpsOverlay(app)
        app.run()
    finally:
        session.stop()
