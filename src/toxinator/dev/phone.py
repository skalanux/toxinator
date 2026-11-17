"""``toxinator dev phone``: HTTPS/WSS server, QR and minimal 3D scene."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from panda3d.core import loadPrcFileData

from toxinator.api.input import InputState
from toxinator.dev.announce import announce_phone
from toxinator.dev.phone_app import PhoneApp
from toxinator.dev.session import start_phone_session

logger = logging.getLogger(__name__)


def _state_line(state: InputState) -> str:
    parts: list[str] = []
    for slot in range(4):
        frame = state.frame(slot)
        info = state.controller(slot)
        if frame is not None:
            latency = (state.timestamp - frame.timestamp) * 1000.0
            action = "A" if frame.button("A") else "-"
            touch = f"{frame.touch[0].x:.2f},{frame.touch[0].y:.2f}" if frame.touch else "-"
            parts.append(
                f"P{slot + 1} {latency:3.0f}ms "
                f"B{frame.orientation[1]:+5.1f} G{frame.orientation[2]:+5.1f} "
                f"touch {touch} {action}"
            )
        elif info is not None:
            parts.append(f"P{slot + 1} gracia")
        else:
            parts.append(f"P{slot + 1} libre")
    return " | ".join(parts)


def run_phone_dev(
    *,
    host: str | None = None,
    port: int = 8443,
    token: str | None = None,
    demo: bool = False,
    headless: bool = False,
    seconds: float | None = None,
    offscreen: bool = False,
    screenshot: Path | None = None,
    screenshot_after: float = 2.0,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    session = start_phone_session(host=host, port=port, token=token, demo=demo)
    if session.host.startswith("127."):
        print(
            "Aviso: el host es loopback; el celular no va a poder conectarse. "
            "Pasá --host con la IP de la LAN.",
            flush=True,
        )

    try:
        announce_phone(session, demo=demo)

        if headless:
            deadline = time.monotonic() + seconds if seconds is not None else None
            last_print = 0.0
            try:
                while True:
                    state = session.hub.poll()
                    now = time.monotonic()
                    if now - last_print >= 0.5:
                        print(_state_line(state), flush=True)
                        last_print = now
                    if deadline is not None and now >= deadline:
                        break
                    time.sleep(0.05)
            except KeyboardInterrupt:
                pass
            return

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
        app = PhoneApp(
            session.hub,
            screenshot=screenshot,
            screenshot_after=screenshot_after,
            seconds=seconds,
            window_type=window_type,
        )
        app.run()
    finally:
        session.stop()
