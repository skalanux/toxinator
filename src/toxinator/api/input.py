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
        "gestures",
        "pointer",
        "touch",
        "haptics",
        "screen",
        "camera",
        "panel",
        "battery",
    }
)

CANONICAL_BUTTONS: frozenset[str] = frozenset(
    {"cross", "circle", "square", "triangle", "options", "l1", "r1"}
)


@dataclass(frozen=True, slots=True)
class TouchPoint:
    """One normalized touch point (0..1 in both axes)."""

    id: int
    x: float
    y: float
    pressure: float = 1.0


@dataclass(frozen=True, slots=True)
class Gesture:
    """A discrete motion intent recognized by the platform.

    ``direction`` is ``up``/``down``/``left``/``right``/``cw``/``ccw``/``none``;
    ``intensity`` is normalized to 0..1. Gestures arrive once, in
    ``InputState.gestures``, and are not part of ``ControllerFrame``.
    """

    slot: int
    controller_id: str
    name: str
    direction: str
    intensity: float
    timestamp: float


@dataclass(frozen=True, slots=True)
class ControllerFrame:
    """One normalized sample from a controller.

    ``orientation`` is relative to the calibrated neutral pose, in degrees:
    ``(alpha, beta, gamma)``. ``gyro`` is in rad/s, ``accel`` in m/s² including
    gravity and ``linear_accel`` in m/s² with gravity removed. ``screen_angle``
    is ``screen.orientation.angle`` (0/90/180/270) and lets the gesture
    recognizer normalize device axes to the screen.
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
    screen_angle: int = 0
    linear_accel: tuple[float, float, float] = (0.0, 0.0, 0.0)

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
    gestures: tuple[Gesture, ...] = ()

    def frame(self, slot: int) -> ControllerFrame | None:
        return self.frames.get(slot)

    def controller(self, slot: int) -> ControllerInfo | None:
        return self.controllers.get(slot)

    def gestures_for(self, slot: int) -> tuple[Gesture, ...]:
        """Return the gestures fired by one slot since the previous poll."""
        return tuple(g for g in self.gestures if g.slot == slot)

    def gesture(self, name: str) -> Gesture | None:
        """Return the first gesture of ``name`` fired since the previous poll."""
        for gesture in self.gestures:
            if gesture.name == name:
                return gesture
        return None

    def primary_slot(self) -> int | None:
        """Return the slot a single-player game should read.

        Phones win over the keyboard/mouse simulator; within a source the
        lowest slot wins. Falls back to any live frame with no controller info.
        """
        if not self.frames:
            return None
        phones = [
            slot
            for slot in self.frames
            if (info := self.controllers.get(slot)) is not None
            and info.source == "phone"
        ]
        return min(phones) if phones else min(self.frames)

    def primary_frame(self) -> ControllerFrame | None:
        slot = self.primary_slot()
        return None if slot is None else self.frames.get(slot)

    def primary_controller(self) -> ControllerInfo | None:
        slot = self.primary_slot()
        return None if slot is None else self.controllers.get(slot)

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
