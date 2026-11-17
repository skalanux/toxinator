"""LIGA · Noche tokens and font helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from panda3d.core import Vec4

NAVY = Vec4(0.055, 0.090, 0.149, 1.0)
NAVY_2 = Vec4(0.075, 0.122, 0.192, 1.0)
NAVY_3 = Vec4(0.031, 0.055, 0.094, 1.0)
BONE = Vec4(0.949, 0.914, 0.855, 1.0)
BONE_2 = Vec4(0.910, 0.847, 0.769, 1.0)
CRIMSON = Vec4(0.690, 0.184, 0.259, 1.0)
CRIMSON_DARK = Vec4(0.478, 0.098, 0.145, 1.0)
GOLD = Vec4(0.890, 0.702, 0.255, 1.0)
JADE = Vec4(0.243, 0.557, 0.494, 1.0)
RED = Vec4(0.878, 0.416, 0.416, 1.0)
MUTED = Vec4(0.357, 0.392, 0.459, 1.0)
LINE = Vec4(0.039, 0.067, 0.110, 1.0)
WHITE = Vec4(1.0, 1.0, 1.0, 1.0)

FONT_DISPLAY_CANDIDATES = (
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf",
)
FONT_UI_CANDIDATES = (
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf",
)
FONT_MONO_CANDIDATES = (
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationMono-Regular.ttf",
)


def _load_first(base: Any, candidates: tuple[str, ...]) -> Any | None:
    for path in candidates:
        if Path(path).is_file():
            try:
                return base.loader.loadFont(path)
            except Exception:
                continue
    return None


def load_fonts(base: Any) -> tuple[Any | None, Any | None, Any | None]:
    return (
        _load_first(base, FONT_DISPLAY_CANDIDATES),
        _load_first(base, FONT_UI_CANDIDATES),
        _load_first(base, FONT_MONO_CANDIDATES),
    )
