from __future__ import annotations

import pytest

from toxinator.input.phone.registry import PhoneRegistry


def test_slots_are_assigned_and_reused() -> None:
    registry = PhoneRegistry(max_slots=2)

    first = registry.join(remote="a", now=1.0)
    second = registry.join(remote="b", now=1.0)
    third = registry.join(remote="c", now=1.0)

    assert first is not None
    assert second is not None
    assert third is None
    assert (first.slot, second.slot) == (0, 1)
    assert registry.connected_count() == 2

    registry.leave(first.slot)
    reused = registry.join(remote="d", now=2.0)
    assert reused is not None
    assert reused.slot == 0


def test_state_and_calibration() -> None:
    registry = PhoneRegistry(max_slots=1)
    connection = registry.join(now=1.0)
    assert connection is not None

    registry.update_state(
        connection.slot,
        {
            "orientation": [10.0, 20.0, 30.0],
            "accel": [0.0, 0.0, 9.81],
            "buttons": ["A"],
            "touch": [{"id": 0, "x": 0.5, "y": 0.5}],
        },
        now=2.0,
    )
    snapshot = registry.snapshot()[0]
    assert snapshot.frame is not None
    assert snapshot.frame.orientation == (10.0, 20.0, 30.0)
    assert snapshot.frame.button("A")

    registry.calibrate(connection.slot)
    registry.update_state(
        connection.slot,
        {"orientation": [20.0, 20.0, 30.0]},
        now=3.0,
    )
    snapshot = registry.snapshot()[0]
    assert snapshot.frame is not None
    assert snapshot.frame.orientation == pytest.approx((10.0, 0.0, 0.0))
