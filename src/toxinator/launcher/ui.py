"""Small 2D helpers for the TOXINATOR launcher."""

from __future__ import annotations

import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectButton import DirectButton
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import LineSegs, TextNode, Texture, Vec4

from toxinator.launcher import art, theme

WHITE = Vec4(1.0, 1.0, 1.0, 1.0)


@dataclass(frozen=True, slots=True)
class Rect:
    x1: float
    x2: float
    z1: float
    z2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.z2 - self.z1

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.z1 + self.z2) / 2.0)

    def grow(self, amount: float) -> Rect:
        return Rect(
            self.x1 - amount,
            self.x2 + amount,
            self.z1 - amount,
            self.z2 + amount,
        )


def image(
    parent: Any,
    texture: Texture,
    rect: Rect,
    *,
    color: Vec4 = WHITE,
    bin_number: int = 10,
    depth_test: bool = False,
) -> OnscreenImage:
    center_x, center_z = rect.center
    node = OnscreenImage(
        image=texture,
        parent=parent,
        pos=(center_x, 0.0, center_z),
        scale=(rect.width / 2.0, 1.0, rect.height / 2.0),
    )
    node.setColor(color)
    node.setTransparency(True)
    node.setBin("fixed", bin_number)
    node.setDepthTest(depth_test)
    node._tox_bin = bin_number
    node._tox_depth = depth_test
    node._tox_color = color
    return node


def swap_image(node: OnscreenImage, texture: Texture) -> None:
    """Replace an image texture and restore the state ``setImage`` drops."""
    node.setImage(texture)
    node.setTransparency(True)
    node.setBin("fixed", getattr(node, "_tox_bin", 10))
    node.setDepthTest(getattr(node, "_tox_depth", False))
    node.setColor(getattr(node, "_tox_color", WHITE))


def rounded(
    parent: Any,
    rect: Rect,
    fill: Vec4,
    *,
    radius: int = 14,
    bin_number: int = 10,
    name: str = "",
) -> OnscreenImage:
    # Size textures in proportion to the rectangle, but cap large panels so
    # startup stays fast. Scaling the radius by the same factor keeps corners
    # visually identical.
    target_width = max(8.0, rect.width * 220.0)
    target_height = max(8.0, rect.height * 220.0)
    factor = min(1.0, 256.0 / max(target_width, target_height))
    texture_width = max(8, round(target_width * factor))
    texture_height = max(8, round(target_height * factor))
    texture_radius = max(2, round(radius * factor))
    texture = art.rounded_texture(
        texture_width,
        texture_height,
        texture_radius,
        fill,
        name=name,
    )
    return image(parent, texture, rect, bin_number=bin_number)


def panel(
    parent: Any,
    rect: Rect,
    fill: Vec4,
    *,
    radius: int = 14,
    bin_number: int = 10,
    shadow: bool = False,
) -> OnscreenImage:
    if shadow:
        rounded(
            parent,
            rect.grow(0.008),
            theme.with_alpha(Vec4(0.0, 0.0, 0.0, 1.0), 0.35),
            radius=radius + 4,
            bin_number=bin_number - 2,
        )
    return rounded(parent, rect, fill, radius=radius, bin_number=bin_number)


def text(
    parent: Any,
    value: str,
    pos: tuple[float, float],
    scale: float,
    color: Vec4,
    font: Any,
    *,
    align: int = TextNode.ALeft,
    bin_number: int = 60,
    shadow: bool = False,
) -> OnscreenText:
    label = OnscreenText(
        text=value,
        parent=parent,
        pos=pos,
        scale=scale,
        fg=color,
        font=font,
        align=align,
        mayChange=True,
        shadow=Vec4(0.0, 0.0, 0.0, 0.5) if shadow else Vec4(0.0, 0.0, 0.0, 0.0),
    )
    label.setBin("fixed", bin_number)
    label.setDepthTest(False)
    return label


def button(
    parent: Any,
    value: str,
    rect: Rect,
    fill: Vec4,
    text_color: Vec4,
    font: Any,
    command: Callable[[], None],
    *,
    text_scale: float = 0.040,
    base_bin: int = 30,
    radius: int = 12,
    ring_color: Vec4 | None = None,
    ring: bool = True,
    text_bin: int | None = None,
) -> tuple[DirectButton, OnscreenImage | None]:
    focus_ring: OnscreenImage | None = None
    if ring:
        focus_ring = rounded(
            parent,
            rect.grow(0.008),
            ring_color or WHITE,
            radius=radius + 3,
            bin_number=base_bin - 6,
            name="focus",
        )
        focus_ring.hide()

    rounded(
        parent,
        rect,
        fill,
        radius=radius,
        bin_number=base_bin - 2,
        name="button",
    )

    control = DirectButton(
        parent=parent,
        text=value,
        text_font=font,
        text_fg=text_color,
        text_scale=text_scale,
        text_align=TextNode.ACenter,
        text_pos=(rect.center[0], rect.center[1] - rect.height * 0.31),
        textMayChange=True,
        frameColor=(0.0, 0.0, 0.0, 0.0),
        frameSize=(rect.x1, rect.x2, rect.z1, rect.z2),
        relief=DGG.FLAT,
        command=command,
        pressEffect=0,
        rolloverSound=None,
        clickSound=None,
    )
    control.setBin("fixed", text_bin or base_bin + 4)
    return control, focus_ring


def pill(
    parent: Any,
    value: str,
    rect: Rect,
    fill: Vec4,
    text_color: Vec4,
    font: Any,
    *,
    text_scale: float = 0.018,
    bin_number: int = 45,
) -> OnscreenText:
    rounded(
        parent,
        rect,
        fill,
        radius=max(4, round(rect.height * 150)),
        bin_number=bin_number - 4,
        name="pill",
    )
    return text(
        parent,
        value,
        (rect.center[0], rect.center[1] - rect.height * 0.32),
        text_scale,
        text_color,
        font,
        align=TextNode.ACenter,
        bin_number=bin_number,
    )


def icon(
    parent: Any,
    kind: str,
    center: tuple[float, float],
    size: float,
    color: Vec4,
    *,
    thickness: float = 2.4,
    bin_number: int = 60,
) -> Any:
    segments = LineSegs(f"icon-{kind}")
    segments.setColor(WHITE)
    segments.setThickness(thickness)
    center_x, center_z = center
    for path in art.icon_lines(kind):
        if not path:
            continue
        first_x, first_z = path[0]
        segments.moveTo(
            center_x + (first_x - 0.5) * size,
            0.0,
            center_z + (first_z - 0.5) * size,
        )
        for x, z in path[1:]:
            segments.drawTo(
                center_x + (x - 0.5) * size,
                0.0,
                center_z + (z - 0.5) * size,
            )
    node = parent.attach_new_node(segments.create())
    node.setColorScale(color)
    node.setBin("fixed", bin_number)
    node.setDepthTest(False)
    return node


def wrap(value: str, width: int = 52) -> str:
    return "\n".join(textwrap.wrap(value, width=width))
