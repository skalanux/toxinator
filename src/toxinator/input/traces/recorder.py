"""Live trace recording: normalized frames plus a gesture sidecar."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from toxinator.api.input import ControllerFrame, ControllerInfo, Gesture
from toxinator.input.traces.trace import (
    ExpectedEvent,
    Trace,
    TraceMeta,
    bucketed,
    expected_path_for,
    write_expected,
    write_trace,
)


class TraceRecorder:
    """Accumulate frames and gestures, then write them at ``stop``.

    Frames are stored with ``t`` relative to the recording start (wall clock),
    matching the trace format's relative-time convention. Gestures are bucketed
    to 0.25 and written to the sidecar.
    """

    def __init__(self) -> None:
        self._path: Path | None = None
        self._start: float | None = None
        self._game = ""
        self._locale = "es"
        self._controllers: list[dict[str, Any]] = []
        self._frames: list[ControllerFrame] = []
        self._expected: list[ExpectedEvent] = []
        self.recording = False

    def start(
        self,
        path: Path,
        *,
        game: str = "",
        locale: str = "es",
        controllers: list[dict[str, Any]] | None = None,
        now: float | None = None,
    ) -> None:
        self._path = path
        self._start = time.monotonic() if now is None else now
        self._game = game
        self._locale = locale
        self._controllers = list(controllers or ())
        self._frames = []
        self._expected = []
        self.recording = True

    def record_frame(self, frame: ControllerFrame) -> None:
        if not self.recording or self._start is None:
            return
        self._frames.append(replace(frame, timestamp=frame.timestamp - self._start))

    def record_controller(self, info: ControllerInfo) -> None:
        if not self.recording:
            return
        if any(entry.get("id") == info.id for entry in self._controllers):
            return
        self._controllers.append(
            {
                "id": info.id,
                "source": info.source,
                "capabilities": sorted(info.capabilities),
                "slot": info.slot,
                "display_name": info.display_name,
            }
        )

    def record_gesture(self, gesture: Gesture) -> None:
        if not self.recording or self._start is None:
            return
        self._expected.append(
            ExpectedEvent(
                t=gesture.timestamp - self._start,
                name=gesture.name,
                direction=gesture.direction,
                intensity=bucketed(gesture.intensity),
            )
        )

    def stop(self) -> Path | None:
        """Write the ``.jsonl`` trace and ``.expected.json`` sidecar."""
        if not self.recording or self._path is None or self._start is None:
            return None
        duration = max((frame.timestamp for frame in self._frames), default=0.0)
        meta = TraceMeta(
            game=self._game,
            locale=self._locale,
            controllers=tuple(self._controllers),
            duration=duration,
        )
        write_trace(self._path, Trace(meta=meta, frames=self._frames, events=[]))
        write_expected(expected_path_for(self._path), self._expected)
        self.recording = False
        self._start = None
        return self._path
