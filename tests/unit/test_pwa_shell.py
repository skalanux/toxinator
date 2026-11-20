from __future__ import annotations

import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "controller-web"


def test_manifest_is_installable_and_icons_exist() -> None:
    manifest = json.loads((WEB / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["name"]
    assert manifest["short_name"]

    purposes = {icon["purpose"] for icon in manifest["icons"]}
    assert "any" in purposes
    assert "maskable" in purposes

    for icon in manifest["icons"]:
        relative = icon["src"].removeprefix("/static/")
        path = WEB / relative
        assert path.is_file(), f"falta el icono {icon['src']}"
        assert icon["type"] == "image/png"


def test_service_worker_shell_files_exist() -> None:
    source = (WEB / "sw.js").read_text(encoding="utf-8")
    match = re.search(r"const SHELL = \[(.*?)\];", source, re.DOTALL)
    assert match is not None

    paths = re.findall(r'"([^"]+)"', match.group(1))
    assert "/" in paths
    assert "/static/app.js" in paths
    assert "/static/vendor/jsqr.js" in paths

    for path in paths:
        if path == "/":
            file = WEB / "index.html"
        elif path == "/manifest.webmanifest":
            file = WEB / "manifest.json"
        else:
            file = WEB / path.removeprefix("/static/")
        assert file.is_file(), f"falta {path} en el shell de la PWA"


def test_controller_shell_has_profiles_and_skins() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'id="skin-button"' in html
    assert 'id="skin-sheet"' in html
    assert 'id="skin-list"' in html
    assert 'id="advanced-button"' in html
    assert 'class="joystick-ring"' in html
    assert 'data-skin="tokyo-night"' in html
    assert 'data-layout="default"' in html
    for skin in ("tokyo-storm", "tokyo-moon", "tokyo-mint"):
        assert f'data-skin="{skin}"' in css
    assert 'message.type === "controller"' in app
    assert "applyAdvanced" in app
    assert "openSkinSheet" in app
    assert "updateLauncherStick" in app
    assert "body.mode-launcher .touchpad" in css
    assert "body.advanced .readout" in css


def test_phone_feedback_shell() -> None:
    app = (WEB / "app.js").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")

    assert "navigator.vibrate" in app
    assert 'message.type === "haptic"' in app
    assert 'message.type === "audio"' in app
    assert "AudioContext" in app
    assert "applyFeedback" in app
    assert "pulseFeedback" in app
    assert "feedback-pulse" in css
    assert 'id="feedback-banner"' in html
    assert "activateFeedback" in app
