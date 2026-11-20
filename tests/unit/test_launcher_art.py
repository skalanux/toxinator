"""Launcher art generation."""

from __future__ import annotations

from toxinator.launcher import art, theme


def test_known_games_have_a_motif() -> None:
    assert art.art_motif("maldito-pino") == "pin"
    assert art.art_motif("kart") == "flag"
    assert art.art_motif("tenis") == "paddle"
    assert art.art_motif("pong") == "pong"
    assert art.art_motif("un-juego-desconocido") in art.FALLBACK_MOTIFS


def test_game_motif_can_override_the_mapping() -> None:
    assert art.art_motif("maldito-pino", "heart") == "heart"
    assert art.art_motif("un-juego-desconocido", "auto") in art.FALLBACK_MOTIFS


def test_game_art_texture_has_requested_size() -> None:
    texture = art.game_art_texture("maldito-pino", "hero", 320, 140, 16)
    assert texture.getXSize() == 320
    assert texture.getYSize() == 140


def test_wallpaper_texture_has_requested_size() -> None:
    texture = art.wallpaper_texture(theme.PALETTE, 320, 180)
    assert texture.getXSize() == 320
    assert texture.getYSize() == 180
