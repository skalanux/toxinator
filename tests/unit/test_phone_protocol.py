from __future__ import annotations

import math

import pytest

from toxinator.input.phone.protocol import build_frame, relative_orientation


def test_build_frame_normalizes_values() -> None:
    frame = build_frame(
        {
            "accel": [1, 2, 3],
            "gyro": [180, 0, -90],
            "orientation": [10, 20, 30],
            "buttons": ["A"],
            "touch": [{"id": 0, "x": 0.25, "y": 0.75, "pressure": 0.5}],
        },
        controller_id="phone-1",
        timestamp=1.0,
        neutral=None,
    )

    assert frame.controller_id == "phone-1"
    assert frame.accel == (1.0, 2.0, 3.0)
    assert frame.gyro[0] == pytest.approx(math.pi)
    assert frame.gyro[2] == pytest.approx(-math.pi / 2)
    assert frame.orientation == (10.0, 20.0, 30.0)
    assert frame.button("A")
    assert frame.touch[0].x == 0.25
    assert frame.touch[0].pressure == 0.5
    assert frame.pointer == (0.25, 0.75)
    assert frame.axes["touch_x"] == 0.25


def test_relative_orientation_wraps_alpha() -> None:
    assert relative_orientation((350.0, 10.0, 5.0), (10.0, 10.0, 0.0)) == (
        -20.0,
        0.0,
        5.0,
    )
    assert relative_orientation((10.0, 20.0, 30.0), None) == (10.0, 20.0, 30.0)


def test_buttons_are_canonical_with_legacy_aliases() -> None:
    frame = build_frame(
        {"buttons": ["A", "circle", "triangle"]},
        controller_id="phone-1",
        timestamp=1.0,
        neutral=None,
    )

    assert frame.button("cross")
    assert frame.button("A")
    assert frame.button("circle")
    assert frame.button("B")
    assert frame.button("triangle")


def test_move_is_normalized_and_exposed_as_axes() -> None:
    frame = build_frame(
        {"move": [1, 1]},
        controller_id="phone-1",
        timestamp=1.0,
        neutral=None,
    )

    assert frame.axes["move_x"] == pytest.approx(2**-0.5)
    assert frame.axes["move_y"] == pytest.approx(2**-0.5)
    assert frame.axes["move_x"] ** 2 + frame.axes["move_y"] ** 2 == pytest.approx(1.0)

    missing = build_frame({}, controller_id="phone-1", timestamp=1.0, neutral=None)
    assert missing.axes["move_x"] == 0.0
    assert missing.axes["move_y"] == 0.0


def test_touch_is_clamped_and_invalid_points_are_ignored() -> None:
    frame = build_frame(
        {
            "touch": [
                {"id": 1, "x": -1, "y": 2},
                {"id": "bad"},
                "not-a-point",
            ]
        },
        controller_id="phone-1",
        timestamp=1.0,
        neutral=None,
    )
    assert len(frame.touch) == 1
    assert frame.touch[0].x == 0.0
    assert frame.touch[0].y == 1.0
