from __future__ import annotations

from importlib.resources import files

from toxinator.api.game import API_VERSION, load_manifest


def test_load_manifest_from_text() -> None:
    manifest = load_manifest(
        """
id = "demo"
name = "Demo Game"
version = "1.2.3"
requires_api = "0.2"
locales = ["es", "en"]
default_locale = "es"
players = [1, 4]
modes = ["partida", "practica"]
"""
    )
    assert manifest.id == "demo"
    assert manifest.version == "1.2.3"
    assert manifest.players == (1, 4)
    assert manifest.modes == ("partida", "practica")


def test_maldito_manifest_is_loadable() -> None:
    text = files("maldito_pino").joinpath("manifest.toml").read_text(encoding="utf-8")
    manifest = load_manifest(text)
    assert manifest.id == "maldito-pino"
    assert manifest.requires_api == API_VERSION
    assert manifest.players == (1, 1)
    assert manifest.default_locale == "es"
    assert manifest.art_motif == "pin"


def test_controller_profile_is_parsed() -> None:
    manifest = load_manifest(
        """
id = "demo"
name = "Demo Game"
version = "0.1.0"
requires_api = "0.2"

[controller]
layout = "motion"
skin = "tokyo-moon"
action = "Tirar"
back = "Volver"
hint = "Incliná para apuntar"
"""
    )
    assert manifest.controller_layout == "motion"
    assert manifest.controller_skin == "tokyo-moon"
    assert manifest.controller_action == "Tirar"
    assert manifest.controller_back == "Volver"
    assert manifest.controller_hint == "Incliná para apuntar"


def test_controller_profile_falls_back_to_defaults() -> None:
    manifest = load_manifest(
        """
id = "demo"
name = "Demo Game"
version = "0.1.0"
requires_api = "0.2"

[controller]
layout = "unknown"
skin = "unknown"
"""
    )
    assert manifest.controller_layout == "default"
    assert manifest.controller_skin == "tokyo-night"


def test_art_motif_is_parsed() -> None:
    manifest = load_manifest(
        """
id = "demo"
name = "Demo Game"
version = "0.1.0"
requires_api = "0.2"

[art]
motif = "flag"
"""
    )
    assert manifest.art_motif == "flag"


def test_art_motif_falls_back_to_auto() -> None:
    manifest = load_manifest(
        """
id = "demo"
name = "Demo Game"
version = "0.1.0"
requires_api = "0.2"

[art]
motif = "unknown"
"""
    )
    assert manifest.art_motif == "auto"
