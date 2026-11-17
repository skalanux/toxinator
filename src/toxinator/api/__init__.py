"""Public API types for the Toxinator prototype."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class Capability(StrEnum):
    BUTTONS = "buttons"
    AXES = "axes"
    MOTION = "motion"
    GYRO = "gyro"
    POINTER = "pointer"
    TOUCH = "touch"
    HAPTICS = "haptics"
    SCREEN = "screen"
    BATTERY = "battery"


@dataclass(frozen=True, slots=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> Vec3:
        magnitude = self.length()
        if magnitude == 0.0:
            return Vec3()
        return Vec3(self.x / magnitude, self.y / magnitude, self.z / magnitude)


@dataclass(frozen=True, slots=True)
class Quat:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0


@dataclass(frozen=True, slots=True)
class TouchPoint:
    id: int
    x: float
    y: float
    pressure: float | None = None


@dataclass(frozen=True, slots=True)
class ControllerFrame:
    timestamp: float
    controller_id: str
    slot: int | None
    connected: bool
    buttons: frozenset[str] = frozenset()
    axes: Mapping[str, float] = field(default_factory=dict)
    accel: Vec3 | None = None
    gyro: Vec3 | None = None
    orientation: Quat | None = None
    pointer: tuple[float, float] | None = None
    touch: tuple[TouchPoint, ...] = ()
    battery: int | None = None
    seq: int | None = None
    raw: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ThrowEvent:
    timestamp: float
    slot: int
    direction: Vec3
    speed: float
    spin: float
    confidence: float
