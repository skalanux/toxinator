from __future__ import annotations

import pytest
from maldito_pino.delivery import (
    MAX_SPEED,
    MIN_SPEED,
    SPIN_SCALE,
    power_from_button,
    power_from_swing,
    speed_from_power,
    spin_from_tilt,
)


def test_spin_from_tilt_scales_and_clamps() -> None:
    assert spin_from_tilt(0.0) == 0.0
    assert spin_from_tilt(0.5) == pytest.approx(SPIN_SCALE / 2.0)
    assert spin_from_tilt(1.0) == SPIN_SCALE
    assert spin_from_tilt(-1.0) == -SPIN_SCALE
    assert spin_from_tilt(2.0) == SPIN_SCALE
    assert spin_from_tilt(-2.0) == -SPIN_SCALE


def test_power_from_button_matches_pre_migration_formula() -> None:
    # No charge, no tilt: 0.70*0 + 0.30*0.5 = 0.15.
    assert power_from_button(0.0, 0.0) == pytest.approx(0.15)
    # Full charge, full tilt: 0.70*1 + 0.30*1.0 = 1.00.
    assert power_from_button(1.0, 1.0) == pytest.approx(1.0)
    # Full charge, full opposite tilt: 0.70*1 + 0.30*0.0 = 0.70.
    assert power_from_button(1.0, -1.0) == pytest.approx(0.70)
    # Full charge, no tilt: 0.70*1 + 0.30*0.5 = 0.85.
    assert power_from_button(1.0, 0.0) == pytest.approx(0.85)
    # Clamps into 0..1 on both ends.
    assert power_from_button(-1.0, -1.0) == 0.0
    assert power_from_button(2.0, 2.0) == 1.0


def test_power_from_swing_scales_arc_and_tilt() -> None:
    # A solid swing (~180° arc) fills the arc term; no tilt leaves 0.85 power.
    assert power_from_swing(0.5, 0.0) == pytest.approx(0.85)
    # The same swing with full pitch tilt reaches full power.
    assert power_from_swing(0.5, 1.0) == pytest.approx(1.0)
    # No swing (intensity 0) and no tilt: 0.30*0.5 = 0.15.
    assert power_from_swing(0.0, 0.0) == pytest.approx(0.15)
    # The arc term clamps above the scale and the whole power clamps to 1.0.
    assert power_from_swing(1.0, 1.0) == 1.0


def test_speed_from_power_spans_the_unchanged_range() -> None:
    assert speed_from_power(0.0) == MIN_SPEED
    assert speed_from_power(1.0) == MAX_SPEED
    assert MIN_SPEED < speed_from_power(0.5) < MAX_SPEED
    # Out-of-range power clamps rather than escaping the speed bounds.
    assert speed_from_power(-1.0) == MIN_SPEED
    assert speed_from_power(2.0) == MAX_SPEED
