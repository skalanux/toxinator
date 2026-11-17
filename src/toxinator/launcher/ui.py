"""Small 2D UI helpers for the LIGA launcher."""

from __future__ import annotations

import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectButton import DirectButton
from direct.gui.DirectFrame import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, Vec4

from toxinator.launcher import theme


@dataclass(frozen=True, slots=True)
class Rect:
    x1: float
    x2: float
    z1: float
    z2: float

    def grow(self, amount: float) -> Rect:
        return Rect(
            self.x1 - amount,
            self.x2 + amount,
            self.z1 - amount,
            self.z2 + amount,
        )


def panel(
    parent: Any,
    rect: Rect,
    color: Vec4,
    *,
    shadow: bool = True,
    border: bool = True,
    base_bin: int = 10,
) -> DirectFrame:
    if shadow:
        shadow_frame = DirectFrame(
            parent=parent,
            frameColor=theme.LINE,
            frameSize=(
                rect.x1 + 0.014,
                rect.x2 + 0.014,
                rect.z1 - 0.014,
                rect.z2 - 0.014,
            ),
            relief=DGG.FLAT,
        )
        shadow_frame.setBin("fixed", base_bin - 2)
    if border:
        border_frame = DirectFrame(
            parent=parent,
            frameColor=theme.LINE,
            frameSize=(
                rect.x1 - 0.008,
                rect.x2 + 0.008,
                rect.z1 - 0.008,
                rect.z2 + 0.008,
            ),
            relief=DGG.FLAT,
        )
        border_frame.setBin("fixed", base_bin - 1)
    frame = DirectFrame(
        parent=parent,
        frameColor=color,
        frameSize=(rect.x1, rect.x2, rect.z1, rect.z2),
        relief=DGG.FLAT,
    )
    frame.setBin("fixed", base_bin)
    return frame


def text(
    parent: Any,
    value: str,
    pos: tuple[float, float],
    scale: float,
    color: Vec4,
    font: Any,
    *,
    align: int = TextNode.ALeft,
    shadow: bool = True,
    bin_number: int = 60,
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
        shadow=Vec4(0.0, 0.0, 0.0, 0.65) if shadow else Vec4(0.0, 0.0, 0.0, 0.0),
    )
    label.setBin("fixed", bin_number)
    label.setDepthTest(False)
    return label


def button(
    parent: Any,
    value: str,
    rect: Rect,
    color: Vec4,
    text_color: Vec4,
    font: Any,
    command: Callable[[], None],
    *,
    text_scale: float = 0.055,
    base_bin: int = 30,
    focus_color: Vec4 | None = None,
) -> tuple[DirectButton, DirectFrame]:
    focus = DirectFrame(
        parent=parent,
        frameColor=focus_color or theme.GOLD,
        frameSize=(
            rect.x1 - 0.012,
            rect.x2 + 0.012,
            rect.z1 - 0.012,
            rect.z2 + 0.012,
        ),
        relief=DGG.FLAT,
    )
    focus.setBin("fixed", base_bin - 10)
    focus.hide()

    control = DirectButton(
        parent=parent,
        text=value,
        text_font=font,
        text_fg=text_color,
        text_scale=text_scale,
        text_align=TextNode.ACenter,
        text_pos=((rect.x1 + rect.x2) / 2.0, (rect.z1 + rect.z2) / 2.0),
        frameColor=color,
        frameSize=(rect.x1, rect.x2, rect.z1, rect.z2),
        relief=DGG.FLAT,
        command=command,
        pressEffect=0,
        rolloverSound=None,
        clickSound=None,
    )
    control.setBin("fixed", base_bin)
    return control, focus


def badge(
    parent: Any,
    value: str,
    rect: Rect,
    color: Vec4,
    text_color: Vec4,
    font: Any,
    *,
    text_scale: float = 0.055,
) -> None:
    frame = DirectFrame(
        parent=parent,
        frameColor=color,
        frameSize=(rect.x1, rect.x2, rect.z1, rect.z2),
        relief=DGG.FLAT,
    )
    frame.setBin("fixed", 50)
    label = text(
        parent,
        value,
        ((rect.x1 + rect.x2) / 2.0, rect.z1 + 0.008),
        text_scale,
        text_color,
        font,
        align=TextNode.ACenter,
        bin_number=62,
    )
    label.setPos((rect.x1 + rect.x2) / 2.0, rect.z1 + 0.008)


def wrap(value: str, width: int = 52) -> str:
    return "\n".join(textwrap.wrap(value, width=width))
