"""Self-signed development certificate for the phone controller."""

from __future__ import annotations

import json
import shutil
import socket
import ssl
import subprocess
import time
from pathlib import Path


def get_lan_ip() -> str:
    """Best-effort LAN IP without sending a packet."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
        if not ip.startswith("127."):
            return ip
    except OSError:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        ip = ""
    return ip if ip and not ip.startswith("127.") else "127.0.0.1"


def ensure_cert(directory: Path, host: str) -> tuple[Path, Path]:
    """Create or reuse a self-signed cert whose SAN includes ``host``."""
    directory.mkdir(parents=True, exist_ok=True)
    cert = directory / "cert.pem"
    key = directory / "key.pem"
    meta = directory / "meta.json"

    if cert.exists() and key.exists() and meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if data.get("host") == host and cert.stat().st_size and key.stat().st_size:
            return cert, key

    openssl = shutil.which("openssl")
    if openssl is None:
        raise RuntimeError(
            "openssl no está instalado; no puedo generar el certificado de desarrollo"
        )

    sans = "DNS:localhost,IP:127.0.0.1"
    if host not in {"127.0.0.1", "localhost"}:
        sans = f"{sans},IP:{host}"

    command = [
        openssl,
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-sha256",
        "-days",
        "365",
        "-keyout",
        str(key),
        "-out",
        str(cert),
        "-subj",
        "/CN=toxinator-dev",
        "-addext",
        f"subjectAltName={sans}",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "openssl no pudo generar el certificado:\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    key.chmod(0o600)
    meta.write_text(
        json.dumps(
            {
                "host": host,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "sans": sans,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return cert, key


def ssl_context(cert: Path, key: Path) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(cert), keyfile=str(key))
    return context
