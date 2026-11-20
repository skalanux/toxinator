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
    assert manifest["orientation"] == "any"
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


def test_controller_shell_has_playstation_buttons_and_layouts() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")

    for name in ("cross", "circle", "square", "triangle", "options", "l1", "r1"):
        assert f'data-button="{name}"' in html
    assert 'data-skin="toxinator"' in html
    assert 'data-orientation="portrait"' in html
    assert 'data-layout="default"' in html
    assert 'id="touch-zone"' in html
    assert 'id="stick-zone"' in html
    assert 'id="panel"' in html
    assert 'id="panel-image"' in html
    assert 'id="camera-button"' in html
    assert 'id="settings-sheet"' in html
    assert 'id="orientation-lock"' in html
    assert 'id="advanced-button"' in html
    assert 'id="feedback-banner"' in html
    assert 'id="readout"' in html
    assert 'id="enable-sensors"' in html

    assert 'body[data-orientation="landscape"] .deck' in css
    assert ".face-button.triangle" in css
    assert ".stick-knob" in css
    assert ".touch-zone.feedback-pulse" in css
    for legacy in ("tokyo-night", "tokyo-storm", "tokyo-moon", "tokyo-mint"):
        assert legacy not in css
        assert legacy not in html


def test_controller_wires_protocol_v2_and_games_profile() -> None:
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "const PROTOCOL = 2" in app
    assert "protocol: PROTOCOL" in app
    assert 'message.type === "controller"' in app
    assert 'message.type === "panel"' in app
    assert "normalizePanel" in app
    assert "applyPanel" in app
    assert "move: state.move" in app
    assert "state.touch" in app
    assert "primary_frame" not in app
    assert '"A"' not in app
    assert "updateLauncherStick" not in app


def test_controller_has_camera_capture_flow() -> None:
    app = (WEB / "app.js").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert "getUserMedia" in app
    assert 'facingMode: { ideal: "user" }' in app
    assert "/api/photo" in app
    assert "X-Toxinator-Token" in app
    assert "toBlob" in app
    assert 'id="camera-sheet"' in html
    assert 'id="camera-capture"' in html


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
