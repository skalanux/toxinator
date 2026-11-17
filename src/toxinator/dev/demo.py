"""A tiny synthetic phone source for demos and headless smoke tests."""

from __future__ import annotations

import math
from collections.abc import Sequence

from toxinator.api.input import ControllerFrame, ControllerInfo
from toxinator.input.source import SourceUpdate


class DemoSource:
    """Move a virtual phone in a slow figure-eight."""

    name = "demo"

    def __init__(self, slot: int = 0, *, buttons: bool = True) -> None:
        self._slot = slot
        self._buttons = buttons
        self._started_at: float | None = None

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def poll(self, now: float) -> Sequence[SourceUpdate]:
        if self._started_at is None:
            self._started_at = now
        elapsed = now - self._started_at
        orientation = (
            0.0,
            30.0 * math.sin(elapsed * 1.2),
            35.0 * math.cos(elapsed * 0.9),
        )
        pressed = self._buttons and int(elapsed) % 2 == 0
        buttons = frozenset({"A"}) if pressed else frozenset()
        frame = ControllerFrame(
            controller_id="demo-1",
            timestamp=now,
            buttons=buttons,
            accel=(0.0, 0.0, 9.81),
            gyro=(0.0, 0.0, 0.0),
            orientation=orientation,
        )
        info = ControllerInfo(
            id="demo-1",
            source="sim",
            capabilities=frozenset({"buttons", "motion", "gyro"}),
            slot=self._slot,
            connected=True,
            display_name="Demo",
        )
        return [SourceUpdate(info, frame)]
