"""Gesture recognizer, protocol fields and hub delivery (milestone 1)."""

from __future__ import annotations

import math
from collections.abc import Sequence

import pytest

from toxinator.api.input import ControllerFrame, ControllerInfo, Gesture
from toxinator.input.gestures import config
from toxinator.input.gestures.recognizer import GestureRecognizer, rotate_screen
from toxinator.input.hub import InputHub
from toxinator.input.phone.protocol import build_frame, screen_angle
from toxinator.input.source import SourceUpdate


def frame(
    *,
    t: float,
    gyro: tuple[float, float, float] = (0.0, 0.0, 0.0),
    linear: tuple[float, float, float] = (0.0, 0.0, 0.0),
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    screen: int = 0,
) -> ControllerFrame:
    return ControllerFrame(
        controller_id="phone-1",
        timestamp=t,
        gyro=gyro,
        linear_accel=linear,
        orientation=orientation,
        screen_angle=screen,
    )


def test_rotate_screen_maps_device_to_screen_axes() -> None:
    assert rotate_screen(1.0, 2.0, 0) == (1.0, 2.0)
    assert rotate_screen(1.0, 2.0, 90) == (-2.0, 1.0)
    assert rotate_screen(1.0, 2.0, 180) == (-1.0, -2.0)
    assert rotate_screen(1.0, 2.0, 270) == (2.0, -1.0)


def test_screen_angle_parses_and_rejects_invalid() -> None:
    assert screen_angle(90) == 90
    assert screen_angle("270") == 270
    assert screen_angle("45") == 0
    assert screen_angle(None) == 0
    assert screen_angle("nope") == 0


def test_build_frame_carries_screen_and_linear() -> None:
    built = build_frame(
        {"screen": 90, "linear": [1, 2, 3], "gyro": [0, 0, 0]},
        controller_id="phone-1",
        timestamp=1.0,
        neutral=None,
    )
    assert built.screen_angle == 90
    assert built.linear_accel == (1.0, 2.0, 3.0)
    missing = build_frame({}, controller_id="phone-1", timestamp=1.0, neutral=None)
    assert missing.screen_angle == 0
    assert missing.linear_accel == (0.0, 0.0, 0.0)


def test_tilt_requires_calibration_and_respects_screen_rotation() -> None:
    recognizer = GestureRecognizer(0, "phone-1")
    assert recognizer.update(frame(t=0.0, orientation=(0, 0, 30)))[0]["tilt_x"] == 0.0

    recognizer.reset()
    recognizer.update(frame(t=0.0, orientation=(0, 0, 0)))
    postures, _ = recognizer.update(frame(t=0.05, orientation=(0, 0, 30)))
    assert postures["tilt_x"] == pytest.approx(
        (30 * (1 - math.exp(-0.05 / config.TILT_SMOOTH_TAU))) / config.TILT_SATURATION
    )
    assert postures["tilt_y"] == 0.0

    rotated = GestureRecognizer(0, "phone-1")
    rotated.reset()
    rotated.update(frame(t=0.0, orientation=(0, 0, 0), screen=90))
    postures, _ = rotated.update(frame(t=0.05, orientation=(0, 0, 30), screen=90))
    assert postures["tilt_x"] == 0.0
    assert postures["tilt_y"] > 0.0


def test_flick_fires_with_direction_and_intensity() -> None:
    recognizer = GestureRecognizer(0, "phone-1")
    recognizer.update(frame(t=0.00, linear=(0, 0, 0)))
    recognizer.update(frame(t=0.02, linear=(0, 20, 0)))
    recognizer.update(frame(t=0.05, linear=(0, 30, 0)))
    _, events = recognizer.update(frame(t=0.20, linear=(0, 3, 0)))

    assert len(events) == 1
    flick = events[0]
    assert flick.name == "flick"
    assert flick.direction == "up"
    assert flick.intensity == pytest.approx(
        (30 - config.FLICK_START) / (config.FLICK_MAX - config.FLICK_START)
    )


def test_flick_rejects_ambiguous_vectors() -> None:
    recognizer = GestureRecognizer(0, "phone-1")
    recognizer.update(frame(t=0.00, linear=(0, 0, 0)))
    recognizer.update(frame(t=0.02, linear=(15, 15, 0)))
    recognizer.update(frame(t=0.05, linear=(15, 15, 0)))
    _, events = recognizer.update(frame(t=0.20, linear=(1, 1, 0)))
    assert events == []


def test_flick_respects_cooldown() -> None:
    recognizer = GestureRecognizer(0, "phone-1")
    recognizer.update(frame(t=0.00, linear=(0, 0, 0)))
    recognizer.update(frame(t=0.02, linear=(0, 20, 0)))
    _, events = recognizer.update(frame(t=0.20, linear=(0, 3, 0)))
    assert len(events) == 1

    # A second flick right after is swallowed by the 300 ms cooldown.
    recognizer.update(frame(t=0.22, linear=(0, 20, 0)))
    recognizer.update(frame(t=0.35, linear=(0, 3, 0)))
    assert recognizer.update(frame(t=0.35, linear=(0, 3, 0)))[1] == []

    # Once cooled down and released, the next flick fires again.
    recognizer.update(frame(t=0.60, linear=(0, 0, 0)))
    recognizer.update(frame(t=0.62, linear=(0, 20, 0)))
    _, events = recognizer.update(frame(t=0.80, linear=(0, 3, 0)))
    assert len(events) == 1


def test_swing_fires_on_arc() -> None:
    recognizer = GestureRecognizer(0, "phone-1")
    recognizer.update(frame(t=0.00, gyro=(0, 0, 0)))
    recognizer.update(frame(t=0.02, gyro=(0, math.radians(200), 0)))
    recognizer.update(frame(t=0.05, gyro=(0, math.radians(250), 0)))
    _, events = recognizer.update(frame(t=0.10, gyro=(0, math.radians(80), 0)))

    assert len(events) == 1
    swing = events[0]
    assert swing.name == "swing"
    assert swing.direction == "up"
    # travel = 200*0.02 + 250*0.03 + 80*0.05 = 15.5 degrees
    assert swing.intensity == pytest.approx(15.5 / config.SWING_INTENSITY)


class FakeGestureSource:
    name = "fake"

    def __init__(self, updates: Sequence[SourceUpdate] | None = None) -> None:
        self.updates = list(updates or ())

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def poll(self, now: float) -> Sequence[SourceUpdate]:
        return self.updates


def _info() -> ControllerInfo:
    return ControllerInfo(
        id="phone-1",
        source="phone",
        capabilities=frozenset({"gestures"}),
        slot=0,
        connected=True,
    )


def _gesture(name: str = "flick", t: float = 1.0) -> Gesture:
    return Gesture(
        slot=0, controller_id="phone-1", name=name, direction="up", intensity=0.5, timestamp=t
    )


def test_hub_delivers_gestures_even_without_a_frame() -> None:
    hub = InputHub([FakeGestureSource([SourceUpdate(_info(), None, (_gesture(),))])])
    state = hub.poll(now=1.0)
    assert state.frame(0) is None
    assert [g.name for g in state.gestures_for(0)] == ["flick"]
    assert state.gesture("flick") is not None


def test_hub_filters_gestures_by_declared_set() -> None:
    source = FakeGestureSource(
        [SourceUpdate(_info(), None, (_gesture("flick"), _gesture("swing")))]
    )
    hub = InputHub([source])
    hub.set_enabled_gestures(["flick"])

    state = hub.poll(now=1.0)
    assert [g.name for g in state.gestures] == ["flick"]

    # None re-enables everything.
    source.updates = [SourceUpdate(_info(), None, (_gesture("swing"),))]
    hub.set_enabled_gestures(None)
    state = hub.poll(now=2.0)
    assert [g.name for g in state.gestures] == ["swing"]
