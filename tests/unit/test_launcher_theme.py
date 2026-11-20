"""Launcher palette."""

from __future__ import annotations

from toxinator.launcher import theme


def test_launcher_uses_tokyo_night() -> None:
    assert theme.PALETTE.id == "tokyo"
    assert theme.PALETTE.name == "Tokyo Night"
