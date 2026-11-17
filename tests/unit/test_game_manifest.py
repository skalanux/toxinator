from __future__ import annotations

from importlib.resources import files

from toxinator.api.game import API_VERSION, load_manifest


def test_load_manifest_from_text() -> None:
    manifest = load_manifest(
        """
id = "demo"
name = "Demo Game"
version = "1.2.3"
requires_api = "0.1"
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
