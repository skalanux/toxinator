"""Shared phone session: HTTP/WS by default, HTTPS/WSS optional, registry and hub."""

from __future__ import annotations

import os
import secrets
import ssl
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from toxinator.dev.cert import ensure_cert, get_lan_ip, ssl_context
from toxinator.dev.cloudflare import CloudflareQuickTunnel
from toxinator.dev.demo import DemoSource
from toxinator.dev.server import DevServer
from toxinator.input.hub import InputHub
from toxinator.input.keyboard import KeyboardMouseSource
from toxinator.input.phone.registry import PhoneRegistry
from toxinator.input.phone.source import PhoneSource
from toxinator.input.source import ControllerSource


@dataclass
class PhoneSession:
    host: str
    port: int
    token: str
    url: str
    hub: InputHub
    registry: PhoneRegistry
    server: DevServer
    keyboard: KeyboardMouseSource | None = None
    tunnel: CloudflareQuickTunnel | None = None

    def set_mode(self, mode: str) -> None:
        self.server.set_mode(mode)

    def set_controller(self, profile: dict[str, Any] | None) -> None:
        self.server.set_controller(profile)

    def set_panel(self, panel: dict[str, Any] | None) -> None:
        self.server.set_panel(panel)

    def set_game_assets(self, game_id: str, root: Path | None) -> None:
        self.server.set_game_assets(game_id, root)

    @property
    def feedback(self) -> PhoneFeedback:
        return PhoneFeedback(self.server)

    def stop(self) -> None:
        if self.tunnel is not None:
            self.tunnel.stop()
            self.tunnel = None
        self.server.stop()
        self.hub.stop()


@dataclass
class PhoneFeedback:
    """Game-facing phone feedback adapter."""

    server: DevServer

    def vibrate(self, pattern: int | Sequence[int], slot: int | None = None) -> None:
        self.server.send_haptic(pattern, slot)

    def tone(
        self,
        frequency: float,
        duration_ms: int,
        *,
        volume: float = 0.35,
        slot: int | None = None,
    ) -> None:
        self.server.send_audio_tone(
            frequency,
            duration_ms,
            volume=volume,
            slot=slot,
        )

    def stop(self, slot: int | None = None) -> None:
        self.server.send_audio_stop(slot)
        self.server.send_haptic([], slot)

    def panel(
        self,
        *,
        title: str = "",
        image: str | None = None,
        fit: str = "contain",
        slot: int | None = None,
    ) -> None:
        if image is None:
            self.server.clear_panel()
            return
        self.server.set_panel({"title": title, "image": image, "fit": fit})

    def clear_panel(self, *, slot: int | None = None) -> None:
        self.server.clear_panel()


def _repo_root() -> Path:
    # src/toxinator/dev/session.py -> repo root
    return Path(__file__).resolve().parents[3]


def start_phone_session(
    *,
    host: str | None = None,
    port: int = 8443,
    token: str | None = None,
    demo: bool = False,
    demo_buttons: bool = True,
    keyboard: bool = True,
    keyboard_slot: int = 4,
    https: bool = False,
    cert: Path | None = None,
    key: Path | None = None,
    cloudflare: bool = False,
) -> PhoneSession:
    lan_host = host or get_lan_ip()
    if lan_host in {"0.0.0.0", ""}:
        lan_host = get_lan_ip()

    session_token = token or secrets.token_urlsafe(18)
    if (cert is None) != (key is None):
        raise RuntimeError("--cert y --key tienen que ir juntos")
    use_tls = https or cert is not None or key is not None
    if cloudflare and use_tls:
        raise RuntimeError(
            "--cloudflare ya entrega HTTPS con certificado válido; "
            "no lo combines con --https, --cert ni --key"
        )
    context: ssl.SSLContext | None = None
    if use_tls:
        if cert is not None and key is not None:
            if not cert.is_file() or not key.is_file():
                raise RuntimeError(f"no encuentro el certificado o la clave: {cert} / {key}")
            context = ssl_context(cert, key)
        else:
            config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            cert_dir = config_home / "toxinator" / "dev-cert"
            cert, key = ensure_cert(cert_dir, lan_host)
            context = ssl_context(cert, key)

    registry = PhoneRegistry(max_slots=4)
    sources: list[ControllerSource] = [PhoneSource(registry)]
    keyboard_source = (
        KeyboardMouseSource(slot=keyboard_slot) if keyboard and not demo else None
    )
    if keyboard_source is not None:
        sources.append(keyboard_source)
    if demo:
        sources.append(DemoSource(buttons=demo_buttons))

    hub = InputHub(sources)
    hub.start()

    server = DevServer(
        host="0.0.0.0",
        port=port,
        controller_web=_repo_root() / "controller-web",
        ssl_context=context,
        token=session_token,
        registry=registry,
    )
    try:
        server.start()
    except Exception:
        hub.stop()
        raise

    tunnel: CloudflareQuickTunnel | None = None
    if cloudflare:
        tunnel = CloudflareQuickTunnel(port)
        try:
            public_url = tunnel.start()
        except Exception:
            server.stop()
            hub.stop()
            raise
        url = f"{public_url}/?token={session_token}"
    else:
        scheme = "https" if use_tls else "http"
        url = f"{scheme}://{lan_host}:{port}/?token={session_token}"

    return PhoneSession(
        host=lan_host,
        port=port,
        token=session_token,
        url=url,
        hub=hub,
        registry=registry,
        server=server,
        keyboard=keyboard_source,
        tunnel=tunnel,
    )
