"""Shared phone session: cert, HTTPS/WSS server, registry and input hub."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from toxinator.dev.cert import ensure_cert, get_lan_ip, ssl_context
from toxinator.dev.demo import DemoSource
from toxinator.dev.server import DevServer
from toxinator.input.hub import InputHub
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

    def set_mode(self, mode: str) -> None:
        self.server.set_mode(mode)

    def stop(self) -> None:
        self.server.stop()
        self.hub.stop()


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
    cert: Path | None = None,
    key: Path | None = None,
) -> PhoneSession:
    lan_host = host or get_lan_ip()
    if lan_host in {"0.0.0.0", ""}:
        lan_host = get_lan_ip()

    session_token = token or secrets.token_urlsafe(18)
    if (cert is None) != (key is None):
        raise RuntimeError("--cert y --key tienen que ir juntos")
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

    return PhoneSession(
        host=lan_host,
        port=port,
        token=session_token,
        url=f"https://{lan_host}:{port}/?token={session_token}",
        hub=hub,
        registry=registry,
        server=server,
    )
