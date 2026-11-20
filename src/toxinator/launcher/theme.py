"""TOXINATOR launcher palette and font helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from panda3d.core import Vec4


def color(value: str, alpha: float = 1.0) -> Vec4:
    """Turn ``#rrggbb`` into a Panda3D colour."""
    raw = value.lstrip("#")
    if len(raw) != 6:
        raise ValueError(f"color inválido: {value}")
    return Vec4(
        int(raw[0:2], 16) / 255.0,
        int(raw[2:4], 16) / 255.0,
        int(raw[4:6], 16) / 255.0,
        alpha,
    )


def with_alpha(value: Vec4, alpha: float) -> Vec4:
    return Vec4(value.x, value.y, value.z, alpha)


@dataclass(frozen=True, slots=True)
class Palette:
    """The launcher colour system."""

    id: str
    name: str
    note: str
    bg: Vec4
    panel: Vec4
    raised: Vec4
    hover: Vec4
    text: Vec4
    muted: Vec4
    accent: Vec4
    accent_ink: Vec4
    status: Vec4
    line: Vec4
    wallpaper_a: Vec4
    wallpaper_b: Vec4


TOKYO_NIGHT = Palette(
    id="tokyo",
    name="Tokyo Night",
    note="azul noche y violeta",
    bg=color("#1a1b26"),
    panel=color("#16161e"),
    raised=color("#292e42"),
    hover=color("#343b58"),
    text=color("#c0caf5"),
    muted=color("#7f8bb3"),
    accent=color("#7aa2f7"),
    accent_ink=color("#16161e"),
    status=color("#9ece6a"),
    line=color("#2f3549"),
    wallpaper_a=color("#16161e"),
    wallpaper_b=color("#1f2335"),
)

PALETTE = TOKYO_NIGHT


_FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

FONT_DISPLAY_CANDIDATES = (
    str(_FONT_DIR / "ArchivoBlack-Regular.ttf"),
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf",
)
FONT_UI_CANDIDATES = (
    str(_FONT_DIR / "IBMPlexSans-Regular.ttf"),
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf",
)
FONT_UI_BOLD_CANDIDATES = (
    str(_FONT_DIR / "IBMPlexSans-SemiBold.ttf"),
    str(_FONT_DIR / "IBMPlexSans-Bold.ttf"),
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf",
)
FONT_MONO_CANDIDATES = (
    str(_FONT_DIR / "IBMPlexMono-Regular.ttf"),
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


def load_fonts(base: Any) -> tuple[Any | None, Any | None, Any | None, Any | None]:
    """Return display, UI, UI semibold and mono fonts."""
    return (
        _load_first(base, FONT_DISPLAY_CANDIDATES),
        _load_first(base, FONT_UI_CANDIDATES),
        _load_first(base, FONT_UI_BOLD_CANDIDATES),
        _load_first(base, FONT_MONO_CANDIDATES),
    )
