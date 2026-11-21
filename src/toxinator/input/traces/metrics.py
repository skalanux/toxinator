"""Detection metrics: run a trace through the recognizer and score it.

Powers the acceptance criteria in ``docs/design/gestures.md``: detection rate
per gesture, zero false positives on the negative suite, aim drift and the
event-to-peak latency in frames.
"""

from __future__ import annotations

from dataclasses import dataclass

from toxinator.api.input import Gesture
from toxinator.input.gestures.recognizer import GestureRecognizer
from toxinator.input.traces.trace import ExpectedEvent, Trace, bucketed

FRAME_SECONDS = 1.0 / 60.0


def recognize(trace: Trace) -> list[Gesture]:
    """Run a fresh recognizer per controller over the trace's frames."""
    recognizers: dict[str, GestureRecognizer] = {}
    events: list[Gesture] = []
    for frame in sorted(trace.frames, key=lambda f: f.timestamp):
        recognizer = recognizers.get(frame.controller_id)
        if recognizer is None:
            recognizer = GestureRecognizer(0, frame.controller_id)
            recognizer.reset()
            recognizers[frame.controller_id] = recognizer
        _, fired = recognizer.update(frame)
        events.extend(fired)
    return events


@dataclass(frozen=True, slots=True)
class GestureResult:
    """One expected gesture scored against the recognized events."""

    expected: ExpectedEvent
    detected: bool
    direction_ok: bool
    intensity_ok: bool
    latency_frames: float | None


def evaluate(trace: Trace, expected: list[ExpectedEvent]) -> list[GestureResult]:
    """Score each expected gesture: detection, direction, intensity and latency."""
    events = recognize(trace)
    results: list[GestureResult] = []
    for exp in expected:
        candidates = [
            event
            for event in events
            if event.name == exp.name and event.direction == exp.direction
        ]
        if not candidates:
            results.append(
                GestureResult(
                    exp,
                    detected=False,
                    direction_ok=False,
                    intensity_ok=False,
                    latency_frames=None,
                )
            )
            continue
        match = min(candidates, key=lambda event: abs(event.timestamp - exp.t))
        intensity_ok = bucketed(match.intensity) == exp.intensity
        results.append(
            GestureResult(
                exp,
                detected=intensity_ok,
                direction_ok=True,
                intensity_ok=intensity_ok,
                latency_frames=(match.timestamp - exp.t) / FRAME_SECONDS,
            )
        )
    return results


def detection_rate(results: list[GestureResult]) -> float:
    if not results:
        return 1.0
    return sum(1 for result in results if result.detected) / len(results)


def false_positives(trace: Trace) -> list[Gesture]:
    """Every recognized event — the negative suite expects this to be empty."""
    return recognize(trace)
