"""Procedural textures for the TOXINATOR launcher.

The launcher generates its own art with Pillow and caches the resulting Panda3D
textures. Game art is an isometric voxel diorama with a per-game motif and small
arcade/HUD accents; there are no external image assets.
"""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from io import BytesIO
from typing import Any

from panda3d.core import PNMImage, StringStream, Texture, Vec4
from PIL import Image, ImageChops, ImageDraw

from toxinator.api.game import ART_MOTIFS, DEFAULT_ART_MOTIF
from toxinator.launcher.theme import Palette, color

# Key art palettes stay independent from the UI palette so games keep an identity
# inside Tokyo Night. Each tuple is (background, primary, secondary, highlight).
ART_PALETTES: tuple[tuple[Vec4, Vec4, Vec4, Vec4], ...] = (
    (color("#1f2335"), color("#7aa2f7"), color("#bb9af7"), color("#c0caf5")),
    (color("#1a1b26"), color("#7aa2f7"), color("#bb9af7"), color("#c0caf5")),
    (color("#1a1b26"), color("#9ece6a"), color("#7dcfff"), color("#c0caf5")),
    (color("#1f2335"), color("#bb9af7"), color("#7aa2f7"), color("#c0caf5")),
    (color("#24283b"), color("#7dcfff"), color("#ff9e64"), color("#c0caf5")),
    (color("#24283b"), color("#ff9e64"), color("#f7768e"), color("#c0caf5")),
)

MOTIFS: dict[str, str] = {
    "maldito-pino": "pin",
    "kart": "flag",
    "tenis": "paddle",
    "pong": "pong",
}
FALLBACK_MOTIFS = ("star", "heart", "coin", "cube")

_CACHE: dict[tuple[object, ...], Texture] = {}

RGBA = tuple[int, int, int, int]
Point = tuple[float, float]


def art_palette(game_id: str) -> tuple[Vec4, Vec4, Vec4, Vec4]:
    digest = hashlib.md5(game_id.encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "big") % len(ART_PALETTES)
    return ART_PALETTES[index]


def art_motif(game_id: str, motif: str | None = None) -> str:
    if motif and motif in ART_MOTIFS and motif != DEFAULT_ART_MOTIF:
        return motif
    if game_id in MOTIFS:
        return MOTIFS[game_id]
    digest = hashlib.md5(game_id.encode("utf-8")).digest()
    return FALLBACK_MOTIFS[digest[4] % len(FALLBACK_MOTIFS)]


def _key_color(value: Vec4) -> tuple[float, float, float, float]:
    return (round(value.x, 4), round(value.y, 4), round(value.z, 4), round(value.w, 4))


def _pil_texture(image: Image.Image) -> Texture:
    """Convert a Pillow RGBA image to a Panda3D texture via an in-memory PNG."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    stream = StringStream(buffer.getvalue())
    pnm = PNMImage()
    if not pnm.read(stream, "art.png"):
        raise RuntimeError("no pude convertir la textura procedural")
    texture = Texture(f"generated-pil-{id(image)}")
    texture.load(pnm)
    texture.setMagfilter(Texture.FTLinear)
    texture.setMinfilter(Texture.FTLinear)
    texture.setWrapU(Texture.WM_clamp)
    texture.setWrapV(Texture.WM_clamp)
    return texture


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return low if value < low else high if value > high else value


def _mix(a: Vec4, b: Vec4, t: float) -> tuple[float, float, float]:
    t = _clamp(t)
    return (
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        a.z + (b.z - a.z) * t,
    )


def _shade(value: Vec4, factor: float) -> Vec4:
    return Vec4(
        _clamp(value.x * factor),
        _clamp(value.y * factor),
        _clamp(value.z * factor),
        value.w,
    )


def _pil(value: Vec4, alpha: float = 1.0) -> RGBA:
    return (
        int(round(_clamp(value.x) * 255)),
        int(round(_clamp(value.y) * 255)),
        int(round(_clamp(value.z) * 255)),
        int(round(_clamp(value.w * alpha) * 255)),
    )


def _pil_shade(value: Vec4, factor: float, alpha: float = 1.0) -> RGBA:
    return _pil(_shade(value, factor), alpha)


def _pil_mix(a: Vec4, b: Vec4, t: float) -> tuple[int, int, int]:
    red, green, blue = _mix(a, b, t)
    return (
        int(round(red * 255)),
        int(round(green * 255)),
        int(round(blue * 255)),
    )


def _vertical_gradient(size: tuple[int, int], top: Vec4, bottom: Vec4) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        red, green, blue = _pil_mix(top, bottom, y / max(height - 1, 1))
        draw.line([(0, y), (width, y)], fill=(red, green, blue, 255))
    return image


def _layer(
    image: Image.Image,
    callback: Any,
) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    callback(ImageDraw.Draw(overlay, "RGBA"))
    return Image.alpha_composite(image, overlay)


def _scanlines(image: Image.Image, color_value: Vec4, alpha: float = 0.06) -> Image.Image:
    step = max(2, image.height // 52)
    fill = _pil(color_value, alpha)

    def draw(draw: Any) -> None:
        for y in range(0, image.height, step):
            draw.line([(0, y), (image.width, y)], fill=fill, width=1)

    return _layer(image, draw)


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        [0, 0, size[0] - 1, size[1] - 1],
        radius=max(0, radius),
        fill=255,
    )
    return mask


def _apply_rounded(image: Image.Image, radius: int) -> Image.Image:
    if radius <= 0:
        return image
    alpha = ImageChops.multiply(image.getchannel("A"), _rounded_mask(image.size, radius))
    image.putalpha(alpha)
    return image


def rounded_texture(
    width: int,
    height: int,
    radius: int,
    fill: Vec4,
    *,
    name: str = "",
) -> Texture:
    """A solid rounded rectangle with an antialiased edge."""
    key = ("rounded", width, height, radius, _key_color(fill), name)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    scale = 2
    image = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        [0, 0, width * scale - 1, height * scale - 1],
        radius=max(0, radius * scale),
        fill=_pil(fill),
    )
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    texture = _pil_texture(image)
    _CACHE[key] = texture
    return texture


def circle_texture(size: int, fill: Vec4) -> Texture:
    key = ("circle", size, _key_color(fill))
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    scale = 3
    image = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse(
        [0, 0, size * scale - 1, size * scale - 1],
        fill=_pil(fill),
    )
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    texture = _pil_texture(image)
    _CACHE[key] = texture
    return texture


def _iso(
    origin: Point,
    x: float,
    y: float,
    z: float,
    tile_w: float,
    tile_h: float,
    z_h: float,
) -> Point:
    return (
        origin[0] + (x - y) * tile_w / 2.0,
        origin[1] + (x + y) * tile_h / 2.0 - z * z_h,
    )


def _face(
    draw: Any,
    points: list[Point],
    fill: RGBA,
    edge: RGBA | None = None,
    width: int = 1,
) -> None:
    draw.polygon(points, fill=fill)
    if edge is not None:
        draw.line(points + [points[0]], fill=edge, width=width)


def _draw_platform(
    draw: Any,
    origin: Point,
    tile_w: float,
    tile_h: float,
    z_h: float,
    palette: tuple[Vec4, Vec4, Vec4, Vec4],
) -> None:
    base, primary, secondary, highlight = palette
    half = 1.72
    thickness = 0.42
    top = _pil_shade(primary, 0.42)
    left = _pil_shade(primary, 0.26)
    right = _pil_shade(primary, 0.19)
    edge = (*_pil_mix(primary, highlight, 0.22), 255)

    # Angular shadow under the floating island.
    _face(
        draw,
        [
            _iso(origin, -half, -half, -thickness - 0.33, tile_w, tile_h, z_h),
            _iso(origin, half, -half, -thickness - 0.33, tile_w, tile_h, z_h),
            _iso(origin, half, half, -thickness - 0.33, tile_w, tile_h, z_h),
            _iso(origin, -half, half, -thickness - 0.33, tile_w, tile_h, z_h),
        ],
        (*_pil_mix(base, Vec4(0.0, 0.0, 0.0, 1.0), 0.55), 255),
    )

    # Side faces.
    _face(
        draw,
        [
            _iso(origin, -half, half, -thickness, tile_w, tile_h, z_h),
            _iso(origin, half, half, -thickness, tile_w, tile_h, z_h),
            _iso(origin, half, half, 0, tile_w, tile_h, z_h),
            _iso(origin, -half, half, 0, tile_w, tile_h, z_h),
        ],
        left,
        edge,
    )
    _face(
        draw,
        [
            _iso(origin, half, half, -thickness, tile_w, tile_h, z_h),
            _iso(origin, half, -half, -thickness, tile_w, tile_h, z_h),
            _iso(origin, half, -half, 0, tile_w, tile_h, z_h),
            _iso(origin, half, half, 0, tile_w, tile_h, z_h),
        ],
        right,
        edge,
    )

    # Top face.
    _face(
        draw,
        [
            _iso(origin, -half, -half, 0, tile_w, tile_h, z_h),
            _iso(origin, half, -half, 0, tile_w, tile_h, z_h),
            _iso(origin, half, half, 0, tile_w, tile_h, z_h),
            _iso(origin, -half, half, 0, tile_w, tile_h, z_h),
        ],
        top,
        edge,
        width=2,
    )

    # Floor grid: game-world structure, no circles.
    for index in range(-1, 2):
        offset = index * 0.82
        draw.line(
            [
                _iso(origin, offset, -half + 0.1, 0.01, tile_w, tile_h, z_h),
                _iso(origin, offset, half - 0.1, 0.01, tile_w, tile_h, z_h),
            ],
            fill=(*_pil_mix(primary, highlight, 0.28), 255),
            width=1,
        )
        draw.line(
            [
                _iso(origin, -half + 0.1, offset, 0.01, tile_w, tile_h, z_h),
                _iso(origin, half - 0.1, offset, 0.01, tile_w, tile_h, z_h),
            ],
            fill=(*_pil_mix(primary, highlight, 0.28), 255),
            width=1,
        )


def _draw_cube(
    draw: Any,
    origin: Point,
    x: float,
    y: float,
    height: float,
    tile_w: float,
    tile_h: float,
    z_h: float,
    palette: tuple[Vec4, Vec4, Vec4, Vec4],
    *,
    secondary: bool = False,
) -> None:
    _, primary, second, highlight = palette
    tone = second if secondary else primary
    half = 0.43
    top = _pil_shade(tone, 1.18)
    left = _pil_shade(tone, 0.86)
    right = _pil_shade(tone, 0.58)
    edge = (*_pil_mix(tone, highlight, 0.24), 255)

    top_points = [
        _iso(origin, x - half, y - half, height, tile_w, tile_h, z_h),
        _iso(origin, x + half, y - half, height, tile_w, tile_h, z_h),
        _iso(origin, x + half, y + half, height, tile_w, tile_h, z_h),
        _iso(origin, x - half, y + half, height, tile_w, tile_h, z_h),
    ]
    left_points = [
        _iso(origin, x - half, y + half, 0, tile_w, tile_h, z_h),
        _iso(origin, x + half, y + half, 0, tile_w, tile_h, z_h),
        _iso(origin, x + half, y + half, height, tile_w, tile_h, z_h),
        _iso(origin, x - half, y + half, height, tile_w, tile_h, z_h),
    ]
    right_points = [
        _iso(origin, x + half, y + half, 0, tile_w, tile_h, z_h),
        _iso(origin, x + half, y - half, 0, tile_w, tile_h, z_h),
        _iso(origin, x + half, y - half, height, tile_w, tile_h, z_h),
        _iso(origin, x + half, y + half, height, tile_w, tile_h, z_h),
    ]
    _face(draw, left_points, left, edge)
    _face(draw, right_points, right, edge)
    _face(draw, top_points, top, edge)
    # A small top highlight reads like a bevel.
    draw.line(
        [
            _iso(origin, x - half + 0.06, y - half + 0.06, height + 0.01, tile_w, tile_h, z_h),
            _iso(origin, x + half - 0.06, y - half + 0.06, height + 0.01, tile_w, tile_h, z_h),
        ],
        fill=(*_pil_mix(tone, highlight, 0.35), 255),
        width=1,
    )


def _star_points(cx: float, cy: float, outer: float, inner: float) -> list[Point]:
    points: list[Point] = []
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        radius = outer if index % 2 == 0 else inner
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return points


def _draw_star(draw: Any, cx: float, cy: float, size: float, fill: RGBA) -> None:
    draw.polygon(_star_points(cx, cy, size, size * 0.44), fill=fill)


def _draw_heart(draw: Any, cx: float, cy: float, size: float, fill: RGBA) -> None:
    points = [
        (cx, cy + size * 0.38),
        (cx - size * 0.50, cy - size * 0.02),
        (cx - size * 0.38, cy - size * 0.34),
        (cx, cy - size * 0.14),
        (cx + size * 0.38, cy - size * 0.34),
        (cx + size * 0.50, cy - size * 0.02),
    ]
    draw.polygon(points, fill=fill)


def _draw_coin(draw: Any, cx: float, cy: float, size: float, fill: RGBA) -> None:
    draw.ellipse(
        [cx - size, cy - size, cx + size, cy + size],
        fill=fill,
        outline=(5, 6, 10, 255),
        width=max(1, int(size * 0.18)),
    )
    draw.line([(cx, cy - size * 0.45), (cx, cy + size * 0.45)], fill=(5, 6, 10, 255), width=1)


def _draw_prop(
    draw: Any,
    motif: str,
    base: Point,
    scale: float,
    palette: tuple[Vec4, Vec4, Vec4, Vec4],
) -> None:
    _, primary, secondary, highlight = palette
    palette_base = palette[0]
    cx, cy = base
    body = _pil(highlight)
    accent = _pil(primary)
    accent2 = _pil(secondary)
    danger = (247, 118, 142, 255)
    dark = (5, 6, 10, 255)

    # Small angular contact shadow.
    draw.polygon(
        [
            (cx - scale * 0.34, cy + scale * 0.03),
            (cx, cy + scale * 0.16),
            (cx + scale * 0.34, cy + scale * 0.03),
            (cx, cy - scale * 0.10),
        ],
        fill=(*_pil_mix(palette_base, Vec4(0.0, 0.0, 0.0, 1.0), 0.55), 255),
    )

    if motif == "pin":
        draw.ellipse(
            [cx - scale * 0.13, cy - scale * 0.92, cx + scale * 0.13, cy - scale * 0.66],
            fill=body,
            outline=dark,
            width=max(1, int(scale * 0.035)),
        )
        draw.polygon(
            [
                (cx - scale * 0.10, cy - scale * 0.70),
                (cx + scale * 0.10, cy - scale * 0.70),
                (cx + scale * 0.16, cy - scale * 0.18),
                (cx + scale * 0.11, cy),
                (cx - scale * 0.11, cy),
                (cx - scale * 0.16, cy - scale * 0.18),
            ],
            fill=body,
            outline=dark,
        )
        for offset in (-0.38, -0.30):
            draw.line(
                [
                    (cx - scale * 0.12, cy + scale * offset),
                    (cx + scale * 0.12, cy + scale * offset),
                ],
                fill=danger,
                width=max(2, int(scale * 0.07)),
            )
        _draw_star(
            draw,
            cx + scale * 0.30,
            cy - scale * 0.92,
            scale * 0.13,
            accent2,
        )
    elif motif == "flag":
        draw.line(
            [(cx, cy), (cx, cy - scale * 1.22)],
            fill=body,
            width=max(2, int(scale * 0.07)),
        )
        flag_w = scale * 0.62
        flag_h = scale * 0.38
        x0 = cx + scale * 0.03
        y0 = cy - scale * 1.18
        draw.rectangle([x0, y0, x0 + flag_w, y0 + flag_h], fill=accent)
        cell_w = flag_w / 3
        cell_h = flag_h / 2
        for row in range(2):
            for col in range(3):
                if (row + col) % 2 == 0:
                    cell_rect = [
                        x0 + col * cell_w,
                        y0 + row * cell_h,
                        x0 + (col + 1) * cell_w,
                        y0 + (row + 1) * cell_h,
                    ]
                    draw.rectangle(cell_rect, fill=body)
        _draw_star(draw, x0 + flag_w * 0.5, y0 + flag_h * 0.5, scale * 0.09, accent2)
    elif motif == "paddle":
        draw.rounded_rectangle(
            [cx - scale * 0.18, cy - scale * 1.02, cx + scale * 0.18, cy - scale * 0.28],
            radius=scale * 0.16,
            fill=accent,
            outline=dark,
            width=max(1, int(scale * 0.035)),
        )
        draw.rectangle(
            [cx - scale * 0.055, cy - scale * 0.30, cx + scale * 0.055, cy],
            fill=body,
        )
        draw.ellipse(
            [cx + scale * 0.22, cy - scale * 0.92, cx + scale * 0.40, cy - scale * 0.74],
            fill=body,
            outline=dark,
        )
        _draw_star(draw, cx - scale * 0.30, cy - scale * 0.82, scale * 0.10, accent2)
    elif motif == "pong":
        for offset in (-0.62, 0.62):
            draw.rounded_rectangle(
                [
                    cx + scale * offset - scale * 0.07,
                    cy - scale * 0.72,
                    cx + scale * offset + scale * 0.07,
                    cy + scale * 0.12,
                ],
                radius=scale * 0.05,
                fill=accent if offset < 0 else body,
                outline=dark,
            )
        draw.ellipse(
            [cx - scale * 0.10, cy - scale * 0.46, cx + scale * 0.10, cy - scale * 0.26],
            fill=accent2,
            outline=dark,
        )
        for index in range(-2, 3):
            draw.line(
                [(cx, cy + scale * 0.04 * index), (cx, cy + scale * 0.04 * index + scale * 0.018)],
                fill=(*_pil_mix(primary, highlight, 0.38), 255),
                width=1,
            )
    elif motif == "heart":
        _draw_heart(draw, cx, cy - scale * 0.46, scale * 0.52, danger)
        _draw_star(draw, cx + scale * 0.40, cy - scale * 1.02, scale * 0.10, accent2)
    elif motif == "coin":
        _draw_coin(draw, cx, cy - scale * 0.40, scale * 0.26, accent)
        _draw_star(draw, cx + scale * 0.30, cy - scale * 0.92, scale * 0.10, body)
    elif motif == "cube":
        _face(
            draw,
            [
                (cx, cy - scale * 0.72),
                (cx + scale * 0.30, cy - scale * 0.55),
                (cx, cy - scale * 0.38),
                (cx - scale * 0.30, cy - scale * 0.55),
            ],
            _pil_shade(primary, 1.18),
            (*_pil_mix(primary, highlight, 0.35), 255),
        )
        _face(
            draw,
            [
                (cx - scale * 0.30, cy - scale * 0.55),
                (cx, cy - scale * 0.38),
                (cx, cy - scale * 0.06),
                (cx - scale * 0.30, cy - scale * 0.24),
            ],
            _pil_shade(primary, 0.82),
        )
        _face(
            draw,
            [
                (cx, cy - scale * 0.38),
                (cx + scale * 0.30, cy - scale * 0.55),
                (cx + scale * 0.30, cy - scale * 0.24),
                (cx, cy - scale * 0.06),
            ],
            _pil_shade(primary, 0.52),
        )
        _draw_star(draw, cx + scale * 0.34, cy - scale * 0.92, scale * 0.10, accent2)
    else:
        _draw_star(draw, cx, cy - scale * 0.50, scale * 0.46, accent2)


def _draw_backdrop(
    image: Image.Image,
    palette: tuple[Vec4, Vec4, Vec4, Vec4],
    shape: str,
) -> Image.Image:
    width, height = image.size
    _, primary, secondary, highlight = palette

    def draw(draw: Any) -> None:
        if shape == "hero":
            draw.polygon(
                [
                    (width * 0.52, height * 0.04),
                    (width * 0.86, height * 0.04),
                    (width * 0.98, height * 0.74),
                    (width * 0.64, height * 0.74),
                ],
                fill=_pil(primary, 0.08),
            )
            draw.line(
                [(width * 0.56, height * 0.95), (width * 0.96, height * 0.16)],
                fill=_pil(secondary, 0.16),
                width=max(2, width // 220),
            )
        else:
            draw.polygon(
                [
                    (width * 0.50, height * 0.06),
                    (width * 0.94, height * 0.44),
                    (width * 0.50, height * 0.88),
                    (width * 0.06, height * 0.44),
                ],
                fill=_pil(primary, 0.07),
            )
        # Floating pixel sparks.
        seed = int.from_bytes(hashlib.md5(str(image.size).encode()).digest()[:4], "big")
        for index in range(10):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            px = width * (0.42 + (seed % 1000) / 1000 * 0.54)
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            py = height * (0.06 + (seed % 1000) / 1000 * 0.82)
            size = max(1, int(width * 0.004))
            draw.rectangle(
                [px, py, px + size, py + size],
                fill=_pil(highlight if index % 2 == 0 else secondary, 0.22),
            )

    return _layer(image, draw)


def _draw_hud(
    image: Image.Image,
    palette: tuple[Vec4, Vec4, Vec4, Vec4],
    shape: str,
) -> Image.Image:
    width, height = image.size
    _, primary, secondary, highlight = palette
    margin = width * 0.038
    bar_w = width * (0.17 if shape == "hero" else 0.22)
    bar_h = max(3, height * 0.022)
    bar_x = width - margin - bar_w
    bar_y = margin

    def draw(draw: Any) -> None:
        draw.rounded_rectangle(
            [bar_x - 2, bar_y - 2, bar_x + bar_w + 2, bar_y + bar_h + 2],
            radius=bar_h,
            fill=(5, 6, 10, 180),
            outline=_pil(highlight, 0.20),
            width=1,
        )
        segments = 5
        gap = max(1, int(width * 0.003))
        seg_w = (bar_w - gap * (segments - 1)) / segments
        for index in range(segments):
            fill = _pil(primary if index < 3 else highlight, 0.85 if index < 3 else 0.14)
            x0 = bar_x + index * (seg_w + gap)
            draw.rounded_rectangle(
                [x0, bar_y, x0 + seg_w, bar_y + bar_h],
                radius=max(1, bar_h // 2),
                fill=fill,
            )
        # Crosshair.
        cross_x = width - margin - width * 0.045
        cross_y = height - margin - height * 0.055
        cross = max(3, width * 0.012)
        draw.line(
            [(cross_x - cross, cross_y), (cross_x + cross, cross_y)],
            fill=_pil(highlight, 0.32),
            width=1,
        )
        draw.line(
            [(cross_x, cross_y - cross), (cross_x, cross_y + cross)],
            fill=_pil(highlight, 0.32),
            width=1,
        )
        draw.rectangle(
            [cross_x - 1, cross_y - 1, cross_x + 1, cross_y + 1],
            fill=_pil(secondary, 0.70),
        )

    return _layer(image, draw)


def _apply_scrim(image: Image.Image, shape: str) -> Image.Image:
    width, height = image.size

    def draw(draw: Any) -> None:
        if shape == "hero":
            for x in range(width):
                t = max(0.0, (width * 0.58 - x) / (width * 0.58))
                alpha = int((t**1.35) * 235)
                if alpha:
                    draw.line([(x, 0), (x, height)], fill=(5, 6, 10, alpha))
            for y in range(int(height * 0.74), height):
                t = (y - height * 0.74) / (height * 0.26)
                draw.line([(0, y), (width, y)], fill=(5, 6, 10, int(t * 120)))
        elif shape == "portrait":
            for y in range(height):
                t = max(0.0, (y - height * 0.84) / (height * 0.16))
                if t:
                    draw.line([(0, y), (width, y)], fill=(5, 6, 10, int(t * 70)))
        else:
            for y in range(height):
                t = max(0.0, (y - height * 0.48) / (height * 0.52))
                if t:
                    draw.line([(0, y), (width, y)], fill=(5, 6, 10, int((t**1.2) * 215)))

    return _layer(image, draw)


def _draw_pickups(
    image: Image.Image,
    palette: tuple[Vec4, Vec4, Vec4, Vec4],
    shape: str,
    origin: Point,
    tile_w: float,
    tile_h: float,
    z_h: float,
) -> Image.Image:
    width, _ = image.size
    _, primary, secondary, highlight = palette

    def draw(draw: Any) -> None:
        if shape == "hero":
            points = [
                (origin[0] - tile_w * 1.25, origin[1] - tile_h * 0.8, "star"),
                (origin[0] + tile_w * 1.05, origin[1] - tile_h * 1.25, "coin"),
                (origin[0] - tile_w * 0.10, origin[1] - tile_h * 1.75, "star"),
            ]
        else:
            points = [
                (origin[0] - tile_w * 0.95, origin[1] - tile_h * 0.7, "star"),
                (origin[0] + tile_w * 0.95, origin[1] - tile_h * 1.1, "coin"),
            ]
        for index, (px, py, kind) in enumerate(points):
            if px < width * 0.42 and shape == "hero":
                continue
            color = _pil(secondary if index % 2 else highlight, 0.80)
            if kind == "star":
                _draw_star(draw, px, py, tile_w * 0.16, color)
            else:
                _draw_coin(draw, px, py, tile_w * 0.12, color)

    return _layer(image, draw)


def _draw_game_art(
    game_id: str,
    shape: str,
    width: int,
    height: int,
    radius: int,
    motif: str | None = None,
) -> Image.Image:
    scale = 3
    canvas_w = width * scale
    canvas_h = height * scale
    base, primary, secondary, highlight = art_palette(game_id)
    motif_name = art_motif(game_id, motif)

    image = _vertical_gradient(
        (canvas_w, canvas_h),
        _shade(base, 0.62),
        _shade(base, 1.18),
    )
    image = _draw_backdrop(image, (base, primary, secondary, highlight), shape)

    if shape == "hero":
        tile_w = canvas_h * 0.32
        origin = (canvas_w * 0.74, canvas_h * 0.60)
        cubes = [
            (-1.02, 0.18, 0.52, True),
            (0.00, 0.00, 1.18, False),
            (1.02, 0.12, 0.78, True),
            (-0.38, -0.92, 0.46, True),
            (0.72, -0.82, 0.40, False),
        ]
        prop_scale = canvas_h * 0.24
    elif shape == "card":
        tile_w = canvas_h * 0.30
        origin = (canvas_w * 0.53, canvas_h * 0.66)
        cubes = [
            (-0.72, 0.18, 0.32, True),
            (0.00, 0.00, 0.58, False),
            (0.72, 0.16, 0.26, True),
        ]
        prop_scale = canvas_h * 0.26
    else:
        tile_w = canvas_h * 0.28
        origin = (canvas_w * 0.52, canvas_h * 0.68)
        cubes = [
            (-0.72, 0.16, 0.28, True),
            (0.00, 0.00, 0.52, False),
            (0.72, 0.14, 0.22, True),
        ]
        prop_scale = canvas_h * 0.25

    tile_h = tile_w * 0.5
    z_h = tile_w * 0.72

    draw = ImageDraw.Draw(image, "RGBA")
    _draw_platform(draw, origin, tile_w, tile_h, z_h, (base, primary, secondary, highlight))

    central = max(cubes, key=lambda item: item[2])
    for x, y, cube_h, is_secondary in sorted(cubes, key=lambda item: item[0] + item[1]):
        _draw_cube(
            draw,
            origin,
            x,
            y,
            cube_h,
            tile_w,
            tile_h,
            z_h,
            (base, primary, secondary, highlight),
            secondary=is_secondary,
        )

    prop_base = _iso(origin, central[0], central[1], central[2], tile_w, tile_h, z_h)
    _draw_prop(
        draw,
        motif_name,
        prop_base,
        prop_scale,
        (base, primary, secondary, highlight),
    )

    image = _draw_pickups(
        image,
        (base, primary, secondary, highlight),
        shape,
        origin,
        tile_w,
        tile_h,
        z_h,
    )
    image = _draw_hud(image, (base, primary, secondary, highlight), shape)
    image = _scanlines(image, highlight, 0.055)
    image = _apply_scrim(image, shape)
    image = _apply_rounded(image, radius * scale)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def wallpaper_texture(selected: Palette, width: int = 480, height: int = 270) -> Texture:
    """A dark gradient with a subtle game grid, angular light and pixel sparks."""
    key = ("wallpaper", selected.id, width, height)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    canvas_scale = 2
    canvas_w = width * canvas_scale
    canvas_h = height * canvas_scale
    image = _vertical_gradient(
        (canvas_w, canvas_h),
        selected.wallpaper_a,
        selected.wallpaper_b,
    )

    def draw(draw: Any) -> None:
        step = max(16, canvas_w // 18)
        for x in range(0, canvas_w, step):
            draw.line([(x, 0), (x, canvas_h)], fill=_pil(selected.accent, 0.020), width=1)
        for y in range(0, canvas_h, step):
            draw.line([(0, y), (canvas_w, y)], fill=_pil(selected.accent, 0.020), width=1)
        draw.polygon(
            [
                (canvas_w * 0.56, -canvas_h * 0.10),
                (canvas_w * 0.78, -canvas_h * 0.10),
                (canvas_w * 1.08, canvas_h * 0.72),
                (canvas_w * 0.84, canvas_h * 0.72),
            ],
            fill=_pil(selected.accent, 0.045),
        )
        draw.polygon(
            [
                (canvas_w * 0.70, -canvas_h * 0.10),
                (canvas_w * 0.82, -canvas_h * 0.10),
                (canvas_w * 1.10, canvas_h * 0.86),
                (canvas_w * 0.96, canvas_h * 0.86),
            ],
            fill=_pil(selected.text, 0.020),
        )
        seed = int.from_bytes(hashlib.md5(selected.id.encode()).digest()[:4], "big")
        for index in range(28):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            px = (seed % 10000) / 10000 * canvas_w
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            py = (seed % 10000) / 10000 * canvas_h
            size = max(1, int(canvas_w * 0.002))
            draw.rectangle(
                [px, py, px + size, py + size],
                fill=_pil(selected.text if index % 3 else selected.accent, 0.16),
            )
        for y in range(int(canvas_h * 0.78), canvas_h):
            t = (y - canvas_h * 0.78) / (canvas_h * 0.22)
            draw.line(
                [(0, y), (canvas_w, y)],
                fill=(4, 5, 9, int(t * 70)),
            )

    image = _layer(image, draw)
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    texture = _pil_texture(image)
    _CACHE[key] = texture
    return texture


def game_art_texture(
    game_id: str,
    shape: str,
    width: int,
    height: int,
    radius: int,
    motif: str | None = None,
) -> Texture:
    """Isometric diorama with a per-game motif and HUD accents."""
    key = ("game-art", game_id, shape, width, height, radius, motif)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    image = _draw_game_art(game_id, shape, width, height, radius, motif)
    texture = _pil_texture(image)
    _CACHE[key] = texture
    return texture


@lru_cache(maxsize=64)
def icon_points(kind: str) -> tuple[tuple[tuple[float, float], ...], ...]:
    """Line paths for the small rail icons, in a 1x1 design box."""
    if kind == "home":
        return (
            ((0.08, 0.44), (0.50, 0.88), (0.92, 0.44)),
            ((0.20, 0.48), (0.20, 0.10), (0.80, 0.10), (0.80, 0.48)),
            ((0.42, 0.10), (0.42, 0.40), (0.58, 0.40), (0.58, 0.10)),
        )
    if kind == "catalog":
        return (
            ((0.10, 0.72), (0.42, 0.72), (0.42, 0.40), (0.10, 0.40), (0.10, 0.72)),
            ((0.58, 0.72), (0.90, 0.72), (0.90, 0.40), (0.58, 0.40), (0.58, 0.72)),
            ((0.10, 0.28), (0.42, 0.28), (0.42, -0.04), (0.10, -0.04), (0.10, 0.28)),
            ((0.58, 0.28), (0.90, 0.28), (0.90, -0.04), (0.58, -0.04), (0.58, 0.28)),
        )
    if kind == "controller":
        return (
            (
                (0.08, 0.40),
                (0.12, 0.16),
                (0.28, 0.08),
                (0.42, 0.20),
                (0.58, 0.20),
                (0.72, 0.08),
                (0.88, 0.16),
                (0.92, 0.40),
                (0.88, 0.64),
                (0.72, 0.72),
                (0.58, 0.58),
                (0.42, 0.58),
                (0.28, 0.72),
                (0.12, 0.64),
                (0.08, 0.40),
            ),
            ((0.35, 0.40), (0.35, 0.40)),
            ((0.65, 0.40), (0.65, 0.40)),
        )
    if kind == "settings":
        return (
            ((0.10, 0.76), (0.90, 0.76)),
            ((0.70, 0.86), (0.70, 0.66)),
            ((0.10, 0.54), (0.90, 0.54)),
            ((0.32, 0.64), (0.32, 0.44)),
            ((0.10, 0.32), (0.90, 0.32)),
            ((0.60, 0.42), (0.60, 0.22)),
        )
    if kind == "play":
        return (((0.30, 0.80), (0.80, 0.50), (0.30, 0.20), (0.30, 0.80)),)
    if kind == "back":
        return (
            ((0.78, 0.50), (0.22, 0.50)),
            ((0.42, 0.30), (0.22, 0.50), (0.42, 0.70)),
        )
    if kind == "plus":
        return (
            ((0.50, 0.20), (0.50, 0.80)),
            ((0.20, 0.50), (0.80, 0.50)),
        )
    return ()


def icon_lines(kind: str) -> tuple[tuple[tuple[float, float], ...], ...]:
    return icon_points(kind)
