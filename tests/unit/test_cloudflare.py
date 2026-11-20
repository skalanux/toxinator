"""Cloudflare Quick Tunnel helpers."""

from __future__ import annotations

import pytest

from toxinator.dev.cloudflare import (
    CLOUDFLARE_URL_RE,
    CloudflareQuickTunnel,
    CloudflareTunnelError,
)


def test_extracts_quick_tunnel_url() -> None:
    line = "2026-11-19T15:00:00Z INF |  https://brave-panda.trycloudflare.com  |"
    match = CLOUDFLARE_URL_RE.search(line)
    assert match is not None
    assert match.group(0) == "https://brave-panda.trycloudflare.com"


def test_missing_cloudflared_has_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("toxinator.dev.cloudflare.shutil.which", lambda _name: None)
    with pytest.raises(CloudflareTunnelError, match="cloudflared"):
        CloudflareQuickTunnel(8443).start()
