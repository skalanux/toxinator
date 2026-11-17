from __future__ import annotations

import threading
import time

from toxinator.api import ControllerFrame


class InputHub:
    """Thread-safe latest-state hub.

    The phone server runs in its own thread and writes frames here; the Panda3D
    task reads the latest frame once per rendered frame.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frames: dict[int, ControllerFrame] = {}
        self._latest_any: ControllerFrame | None = None

    def update(self, frame: ControllerFrame) -> None:
        with self._lock:
            if frame.slot is not None:
                self._frames[frame.slot] = frame
            self._latest_any = frame

    def latest(self, slot: int = 1) -> ControllerFrame | None:
        with self._lock:
            return self._frames.get(slot) or self._latest_any

    def age(self, slot: int = 1) -> float | None:
        frame = self.latest(slot)
        if frame is None:
            return None
        return max(0.0, time.monotonic() - frame.timestamp)
