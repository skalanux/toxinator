"""``toxinator dev phone``: HTTPS/WSS server, QR and minimal 3D scene."""

from __future__ import annotations

import logging
import os
import secrets
import time
from pathlib import Path

import qrcode
from panda3d.core import loadPrcFileData

from toxinator.api.input import InputState
from toxinator.dev.cert import ensure_cert, get_lan_ip, ssl_context
from toxinator.dev.demo import DemoSource
from toxinator.dev.phone_app import PhoneApp
from toxinator.dev.server import DevServer
from toxinator.input.hub import InputHub
from toxinator.input.phone.registry import PhoneRegistry
from toxinator.input.phone.source import PhoneSource
from toxinator.input.source import ControllerSource

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    # src/toxinator/dev/phone.py -> repo root
    return Path(__file__).resolve().parents[3]


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
                f"β{frame.orientation[1]:+5.1f} γ{frame.orientation[2]:+5.1f} "
                f"touch {touch} {action}"
            )
        elif info is not None:
            parts.append(f"P{slot + 1} gracia")
        else:
            parts.append(f"P{slot + 1} libre")
    return " | ".join(parts)


def _print_qr(url: str) -> None:
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


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

    lan_host = host or get_lan_ip()
    if lan_host in {"0.0.0.0", ""}:
        lan_host = get_lan_ip()
    if lan_host.startswith("127."):
        print(
            "Aviso: el host es loopback; el celular no va a poder conectarse. "
            "Pasá --host con la IP de la LAN.",
            flush=True,
        )

    session_token = token or secrets.token_urlsafe(18)
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    cert_dir = config_home / "toxinator" / "dev-cert"
    cert, key = ensure_cert(cert_dir, lan_host)
    context = ssl_context(cert, key)

    controller_web = _repo_root() / "controller-web"
    registry = PhoneRegistry(max_slots=4)
    sources: list[ControllerSource] = [PhoneSource(registry)]
    if demo:
        sources.append(DemoSource())

    hub = InputHub(sources)
    hub.start()

    server = DevServer(
        host="0.0.0.0",
        port=port,
        controller_web=controller_web,
        ssl_context=context,
        token=session_token,
        registry=registry,
    )
    server.start()

    url = f"https://{lan_host}:{port}/?token={session_token}"
    print("\nTOXINATOR · dev phone\n", flush=True)
    print(f"  URL:   {url}", flush=True)
    print("  Wi-Fi: misma red que la consola", flush=True)
    print("  Cert:  aceptá el aviso de certificado autofirmado una vez", flush=True)
    if demo:
        print("  Demo:  fuente sintética activa (P1)", flush=True)
    print("\nEscaneá el QR desde el celular:\n", flush=True)
    _print_qr(url)
    print("\nCtrl+C para salir.\n", flush=True)

    try:
        if headless:
            deadline = time.monotonic() + seconds if seconds is not None else None
            last_print = 0.0
            try:
                while True:
                    state = hub.poll()
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
            hub,
            screenshot=screenshot,
            screenshot_after=screenshot_after,
            seconds=seconds,
            window_type=window_type,
        )
        app.run()
    finally:
        server.stop()
        hub.stop()
