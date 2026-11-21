"""Phone message parsing and frame normalization."""

from __future__ import annotations

import math
from typing import Any

from toxinator.api.input import CANONICAL_BUTTONS, ControllerFrame, TouchPoint

Vec3 = tuple[float, float, float]

BUTTON_ALIASES = {"a": "cross", "b": "circle"}
BUTTON_COMPAT = {"cross": "A", "circle": "B"}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def vec3(value: Any, default: Vec3 = (0.0, 0.0, 0.0)) -> Vec3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return default
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return default


def relative_orientation(raw: Vec3, neutral: Vec3 | None) -> Vec3:
    """Subtract the neutral pose, wrapping alpha around 360 degrees."""
    if neutral is None:
        return raw
    alpha = (raw[0] - neutral[0] + 180.0) % 360.0 - 180.0
    return (alpha, raw[1] - neutral[1], raw[2] - neutral[2])


def normalize_buttons(raw: Any) -> frozenset[str]:
    """Map legacy A/B to canonical names and emit A/B as compatibility aliases."""
    if not isinstance(raw, list):
        return frozenset()
    buttons: set[str] = set()
    for item in raw:
        name = str(item).strip()
        if not name:
            continue
        key = name.lower()
        if key in BUTTON_ALIASES:
            name = BUTTON_ALIASES[key]
        elif key in CANONICAL_BUTTONS:
            name = key
        buttons.add(name)
    for canonical, alias in BUTTON_COMPAT.items():
        if canonical in buttons:
            buttons.add(alias)
    return frozenset(buttons)


def move_axes(value: Any) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return (0.0, 0.0)
    try:
        x = clamp(float(value[0]), -1.0, 1.0)
        y = clamp(float(value[1]), -1.0, 1.0)
    except (TypeError, ValueError):
        return (0.0, 0.0)
    length = math.hypot(x, y)
    if length > 1.0:
        x /= length
        y /= length
    return (x, y)


def screen_angle(value: Any) -> int:
    """Parse ``screen.orientation.angle`` into one of 0/90/180/270."""
    try:
        angle = int(value)
    except (TypeError, ValueError):
        return 0
    return angle if angle in (0, 90, 180, 270) else 0


def build_frame(
    payload: dict[str, Any],
    *,
    controller_id: str,
    timestamp: float,
    neutral: Vec3 | None,
) -> ControllerFrame:
    accel = vec3(payload.get("accel"))
    gyro_deg = vec3(payload.get("gyro"))
    gyro = (math.radians(gyro_deg[0]), math.radians(gyro_deg[1]), math.radians(gyro_deg[2]))
    orientation = relative_orientation(vec3(payload.get("orientation")), neutral)
    linear_accel = vec3(payload.get("linear"))
    screen = screen_angle(payload.get("screen"))

    buttons = normalize_buttons(payload.get("buttons", []))
    move_x, move_y = move_axes(payload.get("move"))

    raw_touch = payload.get("touch", [])
    touches: list[TouchPoint] = []
    if isinstance(raw_touch, list):
        for item in raw_touch:
            if not isinstance(item, dict):
                continue
            try:
                touch_id = int(item.get("id", 0))
                x = clamp(float(item.get("x", 0.5)))
                y = clamp(float(item.get("y", 0.5)))
                pressure = clamp(float(item.get("pressure", 1.0)))
            except (TypeError, ValueError):
                continue
            touches.append(TouchPoint(touch_id, x, y, pressure))

    axes: dict[str, float] = {"move_x": move_x, "move_y": move_y}
    pointer: tuple[float, float] | None = None
    if touches:
        pointer = (touches[0].x, touches[0].y)
        axes["touch_x"] = touches[0].x
        axes["touch_y"] = touches[0].y

    return ControllerFrame(
        controller_id=controller_id,
        timestamp=timestamp,
        buttons=buttons,
        axes=axes,
        accel=accel,
        gyro=gyro,
        orientation=orientation,
        pointer=pointer,
        touch=tuple(touches),
        screen_angle=screen,
        linear_accel=linear_accel,
    )
