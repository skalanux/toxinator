"""``toxinator launcher``: LIGA · Noche home and game launch."""

from __future__ import annotations

import logging
from pathlib import Path

from panda3d.core import loadPrcFileData

from toxinator.core.games import load_catalog
from toxinator.dev.announce import announce_phone
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
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    catalog = load_catalog()
    session = start_phone_session(
        host=host, port=port, token=token, demo=demo, demo_buttons=False
    )
    if session.host.startswith("127."):
        print(
            "Aviso: el host es loopback; el celular no va a poder conectarse. "
            "Pasá --host con la IP de la LAN.",
            flush=True,
        )

    try:
        announce_phone(
            session,
            title="TOXINATOR · LIGA",
            demo=demo,
            extra="Elegí un desafío con las flechas y Enter.",
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

        app = ConsoleApp(
            session.hub,
            catalog,
            session.url,
            window_type=window_type,
            screenshot=screenshot,
            screenshot_after=screenshot_after,
            seconds=seconds,
            set_mode=session.set_mode,
        )
        app.run()
    finally:
        session.stop()
