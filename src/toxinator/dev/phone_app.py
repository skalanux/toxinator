"""Panda3D scene for the ``toxinator dev phone`` cut."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Filename,
    LineSegs,
    TextNode,
    Vec4,
)

from toxinator.api.input import ControllerFrame
from toxinator.input.hub import InputHub
from toxinator.input.keyboard import KeyboardMouseSource

SLOT_COLORS = (
    Vec4(0.69, 0.18, 0.26, 1.0),  # crimson
    Vec4(0.89, 0.70, 0.25, 1.0),  # gold
    Vec4(0.24, 0.56, 0.49, 1.0),  # jade
    Vec4(0.33, 0.52, 0.90, 1.0),  # blue
)
HOMES = ((-3.5, -3.5), (3.5, -3.5), (-3.5, 3.5), (3.5, 3.5))


class PhoneApp(ShowBase):
    """Minimal arena where each connected phone moves a ball."""

    def __init__(
        self,
        hub: InputHub,
        *,
        screenshot: Path | None = None,
        screenshot_after: float = 2.0,
        seconds: float | None = None,
        window_type: str = "onscreen",
        keyboard: KeyboardMouseSource | None = None,
    ) -> None:
        super().__init__(windowType=window_type)
        self.hub = hub
        self.keyboard = keyboard
        if keyboard is not None:
            keyboard.attach(self)
        self.screenshot = screenshot
        self.screenshot_after = screenshot_after
        self.started_at = time.monotonic()
        self.exit_at = self.started_at + seconds if seconds is not None else None

        self.setBackgroundColor(0.025, 0.04, 0.07, 1.0)
        self._build_scene()
        self._build_overlay()
        self.accept("escape", self.userExit)
        self.taskMgr.add(self._update, "phone-update")

    def _build_scene(self) -> None:
        ground = self.loader.loadModel("models/box")
        ground.set_texture_off(1)
        ground.set_scale(10.0, 10.0, 0.1)
        ground.set_pos(-5.0, -5.0, -0.1)
        ground.set_color(Vec4(0.07, 0.09, 0.13, 1.0))
        ground.reparent_to(self.render)

        grid = LineSegs("grid")
        grid.setColor(Vec4(0.16, 0.20, 0.28, 1.0))
        grid.setThickness(1.0)
        for index in range(-5, 6):
            grid.moveTo(index, -5.0, 0.01)
            grid.drawTo(index, 5.0, 0.01)
            grid.moveTo(-5.0, index, 0.01)
            grid.drawTo(5.0, index, 0.01)
        self.render.attach_new_node(grid.create())

        ambient = AmbientLight("ambient")
        ambient.set_color(Vec4(0.58, 0.58, 0.62, 1.0))
        self.render.set_light(self.render.attach_new_node(ambient))

        key = DirectionalLight("key")
        key.set_color(Vec4(1.0, 0.94, 0.82, 1.0))
        key_node = self.render.attach_new_node(key)
        key_node.set_hpr(30.0, -55.0, 0.0)
        self.render.set_light(key_node)

        self.markers = []
        for index, color in enumerate(SLOT_COLORS):
            marker = self.loader.loadModel("models/misc/sphere")
            marker.set_texture_off(1)
            marker.set_scale(0.45)
            marker.set_color(color)
            marker.set_pos(*HOMES[index], 0.45)
            marker.reparent_to(self.render)
            self.markers.append(marker)

        self.cam.set_pos(0.0, -10.0, 7.0)
        self.cam.look_at(0.0, 0.0, 0.0)
        self.camLens.set_fov(55.0)

    def _build_overlay(self) -> None:
        OnscreenText(
            text="TOXINATOR / DEV PHONE",
            pos=(-1.32, 0.94),
            align=TextNode.ALeft,
            scale=0.058,
            fg=Vec4(0.89, 0.70, 0.25, 1.0),
            shadow=Vec4(0.0, 0.0, 0.0, 0.6),
        )
        OnscreenText(
            text="Incliná el teléfono o tocá la pantalla para mover la bola. A = pulso.",
            pos=(-1.32, 0.88),
            align=TextNode.ALeft,
            scale=0.034,
            fg=Vec4(0.72, 0.76, 0.84, 1.0),
            shadow=Vec4(0.0, 0.0, 0.0, 0.6),
        )
        self.overlay = OnscreenText(
            text="",
            pos=(-1.32, 0.80),
            align=TextNode.ALeft,
            scale=0.036,
            fg=Vec4(0.95, 0.92, 0.84, 1.0),
            shadow=Vec4(0.0, 0.0, 0.0, 0.6),
            mayChange=True,
        )
        OnscreenText(
            text="Esc: salir",
            pos=(0.0, -0.95),
            align=TextNode.ACenter,
            scale=0.032,
            fg=Vec4(0.52, 0.56, 0.64, 1.0),
        )

    def _move_marker(self, slot: int, frame: ControllerFrame | None) -> None:
        marker = self.markers[slot]
        if frame is None:
            home_x, home_y = HOMES[slot]
            marker.set_pos(home_x, home_y, 0.45)
            marker.set_color_scale(0.18)
            return

        if frame.pointer is not None:
            x = (frame.pointer[0] - 0.5) * 9.0
            y = (0.5 - frame.pointer[1]) * 9.0
        else:
            x = max(-4.5, min(4.5, frame.orientation[2] / 45.0 * 4.5))
            y = max(-4.5, min(4.5, frame.orientation[1] / 45.0 * 4.5))
        marker.set_pos(x, y, 0.45)
        marker.set_color_scale(1.0 if frame.button("cross") else 0.85)

    def _update(self, task: Any) -> Any:
        state = self.hub.poll()
        lines: list[str] = []
        for slot in range(4):
            info = state.controller(slot)
            frame = state.frame(slot)
            self._move_marker(slot, frame)
            if frame is not None:
                latency = max(0.0, (state.timestamp - frame.timestamp) * 1000.0)
                beta = frame.orientation[1]
                gamma = frame.orientation[2]
                touch = (
                    f"{frame.pointer[0]:.2f},{frame.pointer[1]:.2f}"
                    if frame.pointer
                    else "—"
                )
                action = "X" if frame.button("cross") else "—"
                lines.append(
                    f"P{slot + 1} {info.display_name if info else 'phone'}  "
                    f"{latency:3.0f} ms  B {beta:+5.1f}°  G {gamma:+5.1f}°  "
                    f"touch {touch}  {action}"
                )
            elif info is not None:
                lines.append(f"P{slot + 1} {info.display_name}  gracia")
            else:
                lines.append(f"P{slot + 1} libre")
        self.overlay.setText("\n".join(lines))

        now = time.monotonic()
        if self.screenshot is not None and now - self.started_at >= self.screenshot_after:
            if self.win is not None:
                self.win.saveScreenshot(Filename.from_os_specific(str(self.screenshot)))
                print(f"screenshot: {self.screenshot}", flush=True)
            self.userExit()
        elif self.exit_at is not None and now >= self.exit_at:
            self.userExit()
        return task.cont
