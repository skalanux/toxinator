"""Trace JSONL format: normalized frames, meta and event lines.

The format is versioned JSONL (``trace_version`` 1) and matches
``docs/design/testing.md``. A trace file holds one ``meta`` line, then ``frame``
lines (normalized ``ControllerFrame``), then optional ``event`` lines. Gesture
ground truth lives in a sidecar ``*.expected.json`` next to the trace (see
``docs/design/gestures.md``).

Frames carry the sensors needed to re-run the gesture recognizer
deterministically: ``accel``, ``gyro``, ``linear_accel``, ``orientation`` and
``screen_angle`` are optional fields with sensible defaults.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from toxinator import __version__
from toxinator.api.input import ControllerFrame, TouchPoint

TRACE_VERSION = 1
EXPECTED_BUCKET = 0.25


def bucketed(intensity: float) -> float:
    """Round ``intensity`` to the nearest 0.25 bucket, clamped to 0..1."""
    clamped = max(0.0, min(1.0, intensity))
    return round(clamped / EXPECTED_BUCKET) * EXPECTED_BUCKET


@dataclass(frozen=True, slots=True)
class TraceMeta:
    """The ``meta`` line: identity and reproduction context for a trace."""

    app_version: str = __version__
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    game: str = ""
    locale: str = "es"
    platform: str = field(default_factory=platform.platform)
    controllers: tuple[dict[str, Any], ...] = ()
    seed: int | None = None
    duration: float = 0.0


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """A lifecycle event line (join/leave/calibration) inside a trace."""

    t: float
    kind: str
    controller_id: str = ""
    slot: int = 0


@dataclass(frozen=True, slots=True)
class ExpectedEvent:
    """One ground-truth gesture in a ``*.expected.json`` sidecar."""

    t: float
    name: str
    direction: str
    intensity: float  # already bucketed to 0.25


@dataclass
class Trace:
    """A parsed trace: meta, normalized frames and lifecycle events."""

    meta: TraceMeta
    frames: list[ControllerFrame] = field(default_factory=list)
    events: list[TraceEvent] = field(default_factory=list)

    @property
    def duration(self) -> float:
        if not self.frames:
            return 0.0
        return max(frame.timestamp for frame in self.frames)

    def controllers_by_id(self) -> dict[str, dict[str, Any]]:
        return {controller["id"]: controller for controller in self.meta.controllers}


def _floats(value: Any, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return default
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return default


def frame_to_dict(frame: ControllerFrame) -> dict[str, Any]:
    """Serialize a normalized frame's fields (``t``/``controller_id`` aside)."""
    return {
        "buttons": sorted(frame.buttons),
        "axes": dict(frame.axes),
        "accel": list(frame.accel),
        "gyro": list(frame.gyro),
        "orientation": list(frame.orientation),
        "pointer": list(frame.pointer) if frame.pointer is not None else None,
        "touch": [
            {"id": point.id, "x": point.x, "y": point.y, "pressure": point.pressure}
            for point in frame.touch
        ],
        "screen_angle": frame.screen_angle,
        "linear_accel": list(frame.linear_accel),
    }


def frame_from_dict(
    data: dict[str, Any], *, controller_id: str, t: float
) -> ControllerFrame:
    """Rebuild a normalized frame from a trace line, tolerating missing fields."""
    buttons: frozenset[str] = frozenset()
    raw_buttons = data.get("buttons")
    if isinstance(raw_buttons, list):
        buttons = frozenset(str(item) for item in raw_buttons)

    axes: dict[str, float] = {}
    raw_axes = data.get("axes")
    if isinstance(raw_axes, dict):
        for key, value in raw_axes.items():
            try:
                axes[str(key)] = float(value)
            except (TypeError, ValueError):
                continue

    touches: list[TouchPoint] = []
    raw_touch = data.get("touch")
    if isinstance(raw_touch, list):
        for item in raw_touch:
            if not isinstance(item, dict):
                continue
            try:
                touches.append(
                    TouchPoint(
                        int(item.get("id", 0)),
                        float(item.get("x", 0.5)),
                        float(item.get("y", 0.5)),
                        float(item.get("pressure", 1.0)),
                    )
                )
            except (TypeError, ValueError):
                continue

    pointer: tuple[float, float] | None = None
    raw_pointer = data.get("pointer")
    if isinstance(raw_pointer, (list, tuple)) and len(raw_pointer) == 2:
        try:
            pointer = (float(raw_pointer[0]), float(raw_pointer[1]))
        except (TypeError, ValueError):
            pointer = None

    screen = data.get("screen_angle", 0)
    try:
        screen_angle = int(screen)
    except (TypeError, ValueError):
        screen_angle = 0

    return ControllerFrame(
        controller_id=controller_id,
        timestamp=t,
        buttons=buttons,
        axes=axes,
        accel=_floats(data.get("accel"), (0.0, 0.0, 0.0)),
        gyro=_floats(data.get("gyro"), (0.0, 0.0, 0.0)),
        orientation=_floats(data.get("orientation"), (0.0, 0.0, 0.0)),
        pointer=pointer,
        touch=tuple(touches),
        screen_angle=screen_angle,
        linear_accel=_floats(data.get("linear_accel"), (0.0, 0.0, 0.0)),
    )


def _meta_to_dict(meta: TraceMeta) -> dict[str, Any]:
    return {
        "type": "meta",
        "trace_version": TRACE_VERSION,
        "app_version": meta.app_version,
        "created_at": meta.created_at,
        "game": meta.game,
        "locale": meta.locale,
        "platform": meta.platform,
        "controllers": list(meta.controllers),
        "seed": meta.seed,
        "duration": meta.duration,
    }


def _meta_from_dict(data: dict[str, Any]) -> TraceMeta:
    controllers: tuple[dict[str, Any], ...] = ()
    raw_controllers = data.get("controllers")
    if isinstance(raw_controllers, list):
        controllers = tuple(
            item for item in raw_controllers if isinstance(item, dict)
        )
    return TraceMeta(
        app_version=str(data.get("app_version", __version__)),
        created_at=str(data.get("created_at", "")),
        game=str(data.get("game", "")),
        locale=str(data.get("locale", "es")),
        platform=str(data.get("platform", platform.platform())),
        controllers=controllers,
        seed=data.get("seed"),
        duration=float(data.get("duration", 0.0)),
    )


def write_trace(path: Path, trace: Trace) -> None:
    """Write a trace as versioned JSONL (meta + frame + event lines)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = replace(trace.meta, duration=trace.duration)
    lines: list[str] = [json.dumps(_meta_to_dict(meta), ensure_ascii=False)]
    for frame in trace.frames:
        lines.append(
            json.dumps(
                {
                    "type": "frame",
                    "t": frame.timestamp,
                    "controller_id": frame.controller_id,
                    **frame_to_dict(frame),
                },
                ensure_ascii=False,
            )
        )
    for event in trace.events:
        lines.append(
            json.dumps(
                {
                    "type": "event",
                    "t": event.t,
                    "kind": event.kind,
                    "controller_id": event.controller_id,
                    "slot": event.slot,
                },
                ensure_ascii=False,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_trace(path: Path) -> Trace:
    """Read and lightly validate a trace; raises on a missing/invalid meta."""
    meta: TraceMeta | None = None
    frames: list[ControllerFrame] = []
    events: list[TraceEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}: línea JSON inválida: {error}") from error
        if not isinstance(data, dict):
            continue
        kind = data.get("type")
        if kind == "meta":
            version = data.get("trace_version", TRACE_VERSION)
            if version != TRACE_VERSION:
                raise ValueError(
                    f"{path}: trace_version {version!r} no soportado (esperado {TRACE_VERSION})"
                )
            meta = _meta_from_dict(data)
        elif kind == "frame":
            try:
                t = float(data["t"])
                controller_id = str(data["controller_id"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"{path}: frame sin t o controller_id") from error
            frames.append(frame_from_dict(data, controller_id=controller_id, t=t))
        elif kind == "event":
            try:
                events.append(
                    TraceEvent(
                        t=float(data["t"]),
                        kind=str(data["kind"]),
                        controller_id=str(data.get("controller_id", "")),
                        slot=int(data.get("slot", 0)),
                    )
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"{path}: event inválido") from error
    if meta is None:
        raise ValueError(f"{path}: falta la línea meta")
    return Trace(meta=meta, frames=frames, events=events)


def expected_path_for(trace_path: Path) -> Path:
    """``foo.jsonl`` -> ``foo.expected.json``."""
    return trace_path.with_suffix(".expected.json")


def write_expected(path: Path, events: list[ExpectedEvent]) -> None:
    """Write a ``*.expected.json`` sidecar with bucketed gesture ground truth."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "expected",
        "trace_version": TRACE_VERSION,
        "events": [
            {
                "t": event.t,
                "name": event.name,
                "direction": event.direction,
                "intensity": event.intensity,
            }
            for event in events
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_expected(path: Path) -> list[ExpectedEvent]:
    """Read a sidecar; returns an empty list when the file is missing."""
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    events: list[ExpectedEvent] = []
    for item in data.get("events", []):
        events.append(
            ExpectedEvent(
                t=float(item["t"]),
                name=str(item["name"]),
                direction=str(item["direction"]),
                intensity=float(item["intensity"]),
            )
        )
    return events
