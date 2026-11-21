"""Pure delivery math: map gestures and buttons to ball speed and spin.

Maldito Pino now reads the ``tilt`` posture and the ``swing`` event from the
console instead of raw phone orientation, so the mapping lives here free of
Panda3D and is unit-testable. The button fallback (hold/release) reuses the
same helpers with the charge accumulated while the action is held, keeping the
behaviour of the pre-migration game.
"""

from __future__ import annotations

# Ball speed range (m/s) and spin scale (rad/s around the roll axis), unchanged
# from the pre-migration game so a recorded trace keeps the same behaviour.
MIN_SPEED = 5.5
MAX_SPEED = 10.0
SPIN_SCALE = 12.0

# A ``swing`` event's intensity is ``arc / 360°``; a realistic bowling swing
# lands well under 360°, so scale it so a solid swing (~0.5) fills the arc term.
# Tune here (or in the gestures lab, #19) rather than in game.py.
SWING_POWER_SCALE = 2.0

# Power blend: how much comes from the hold/arc term vs the pitch tilt. The
# 70/30 split mirrors the pre-migration ``0.70*charge + 0.30*(0.5 + 0.5*beta)``.
CHARGE_WEIGHT = 0.70
TILT_WEIGHT = 0.30


def _clamp_unit(value: float) -> float:
    """Clamp a signed input to -1..1."""
    return max(-1.0, min(1.0, value))


def _clamp01(value: float) -> float:
    """Clamp a power to 0..1."""
    return max(0.0, min(1.0, value))


def _power(charge: float, tilt_y: float) -> float:
    """Blend a hold/arc term (0..1) with the pitch tilt (-1..1)."""
    beta = _clamp_unit(tilt_y)
    return _clamp01(CHARGE_WEIGHT * _clamp01(charge) + TILT_WEIGHT * (0.5 + 0.5 * beta))


def spin_from_tilt(tilt_x: float) -> float:
    """Map the ``tilt`` roll posture (-1..1) to spin in [-SPIN_SCALE, SPIN_SCALE]."""
    return _clamp_unit(tilt_x) * SPIN_SCALE


def power_from_button(charge: float, tilt_y: float) -> float:
    """Fallback power while charging: hold time plus pitch tilt."""
    return _power(charge, tilt_y)


def power_from_swing(intensity: float, tilt_y: float) -> float:
    """Power from a ``swing`` event's arc (scaled) plus the pitch tilt."""
    return _power(intensity * SWING_POWER_SCALE, tilt_y)


def speed_from_power(power: float) -> float:
    """Ball launch speed (m/s) for a normalized power (0..1)."""
    return MIN_SPEED + (MAX_SPEED - MIN_SPEED) * _clamp01(power)
