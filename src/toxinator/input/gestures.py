from __future__ import annotations

from collections import deque

from toxinator.api import ControllerFrame, ThrowEvent


class ThrowDetector:
    """Very small throw detector for the phone prototype.

    It keeps a short rolling window, starts when the throw button is held and
    computes a throw when the button is released. The exact thresholds are the
    thing this prototype is meant to tune.
    """

    def __init__(self, window_seconds: float = 0.8) -> None:
        self._window: deque[ControllerFrame] = deque()
        self._window_seconds = window_seconds
        self._holding = False

    def update(self, frame: ControllerFrame) -> ThrowEvent | None:
        self._window.append(frame)
        cutoff = frame.timestamp - self._window_seconds
        while self._window and self._window[0].timestamp < cutoff:
            self._window.popleft()

        holding = bool({"b", "throw"} & frame.buttons)
        event = None
        if self._holding and not holding:
            event = self._make_throw(frame)
        self._holding = holding
        return event

    def _make_throw(self, frame: ControllerFrame) -> ThrowEvent | None:
        samples = [sample for sample in self._window if sample.accel is not None]
        if not samples:
            return None

        peak = max(samples, key=lambda sample: sample.accel.length())  # type: ignore[union-attr]
        accel = peak.accel
        assert accel is not None
        speed = accel.length()
        direction = accel.normalized()
        spin = peak.gyro.z if peak.gyro is not None else accel.x
        confidence = min(1.0, speed / 2.0)
        return ThrowEvent(
            timestamp=frame.timestamp,
            slot=frame.slot or 1,
            direction=direction,
            speed=speed,
            spin=spin,
            confidence=confidence,
        )
