"""Canonical input types shared by the console and games."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

Capability = str

CAPABILITIES: frozenset[str] = frozenset(
    {
        "buttons",
        "axes",
        "motion",
        "gyro",
        "pointer",
        "touch",
        "haptics",
        "screen",
        "battery",
    }
)


@dataclass(frozen=True, slots=True)
class TouchPoint:
    """One normalized touch point (0..1 in both axes)."""

    id: int
    x: float
    y: float
    pressure: float = 1.0


@dataclass(frozen=True, slots=True)
class ControllerFrame:
    """One normalized sample from a controller.

    ``orientation`` is relative to the calibrated neutral pose, in degrees:
    ``(alpha, beta, gamma)``. ``gyro`` is in rad/s and ``accel`` in m/s².
    """

    controller_id: str
    timestamp: float
    buttons: frozenset[str] = field(default_factory=frozenset)
    axes: Mapping[str, float] = field(default_factory=dict)
    accel: tuple[float, float, float] = (0.0, 0.0, 0.0)
    gyro: tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    pointer: tuple[float, float] | None = None
    touch: tuple[TouchPoint, ...] = ()

    def button(self, name: str) -> bool:
        return name in self.buttons

    def axis(self, name: str) -> float:
        return self.axes.get(name, 0.0)


@dataclass(frozen=True, slots=True)
class ControllerInfo:
    """Identity and capabilities of a connected controller."""

    id: str
    source: str
    capabilities: frozenset[str]
    slot: int
    connected: bool
    display_name: str = ""
    battery: float | None = None


@dataclass(frozen=True, slots=True)
class InputState:
    """Immutable snapshot of all slots for one frame."""

    timestamp: float
    frames: Mapping[int, ControllerFrame]
    controllers: Mapping[int, ControllerInfo]

    def frame(self, slot: int) -> ControllerFrame | None:
        return self.frames.get(slot)

    def controller(self, slot: int) -> ControllerInfo | None:
        return self.controllers.get(slot)

    @property
    def connected_slots(self) -> tuple[int, ...]:
        return tuple(
            slot for slot, info in self.controllers.items() if info.connected
        )


@dataclass(frozen=True, slots=True)
class InputEvent:
    """Lifecycle event emitted by the hub."""

    kind: str
    slot: int
    controller_id: str
    timestamp: float
