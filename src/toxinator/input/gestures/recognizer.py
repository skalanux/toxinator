"""Gesture recognition over normalized ``ControllerFrame`` samples.

One recognizer per slot and source; it is stateful and time-aware. Recognizes
the ``tilt``, ``steer`` and ``aim`` postures plus the ``flick``, ``swing``,
``twist``, ``shake`` and ``flip`` events.
"""

from __future__ import annotations

import math

from toxinator.api.input import ControllerFrame, Gesture
from toxinator.input.gestures import config

_SCREEN_ANGLES = (0, 90, 180, 270)


def rotate_screen(x: float, y: float, angle: int) -> tuple[float, float]:
    """Rotate a device-frame ``(x, y)`` pair into screen axes.

    Matches the table in ``docs/design/gestures.md``: ``screen.orientation.angle``
    is the angle by which the UI is rotated, so the device components map to the
    screen components through the inverse rotation.
    """
    if angle == 90:
        return (-y, x)
    if angle == 180:
        return (-x, -y)
    if angle == 270:
        return (y, -x)
    return (x, y)


def _deadzone(value: float, zone: float) -> float:
    return value if abs(value) > zone else 0.0


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class GestureRecognizer:
    """Stateful recognizer bound to one slot and controller id."""

    def __init__(self, slot: int, controller_id: str) -> None:
        self._slot = slot
        self._controller_id = controller_id
        self._last_t: float | None = None
        self._calibrated = False
        self._sensitivity = config.AIM_SENSITIVITY

        self._tilt_x = 0.0
        self._tilt_y = 0.0

        self._aim_x = 0.5
        self._aim_y = 0.5

        self._flick_armed = True
        self._flick_open_t: float | None = None
        self._flick_peak = 0.0
        self._flick_peak_vec = (0.0, 0.0)
        self._flick_last = -math.inf

        self._swing_open = False
        self._swing_start = 0.0
        self._swing_travel = 0.0
        self._swing_peak_rate = 0.0
        self._swing_peak_vec = (0.0, 0.0)
        self._swing_last = -math.inf

        self._twist_open = False
        self._twist_start = 0.0
        self._twist_angle = 0.0
        self._twist_last = -math.inf

        self._shake_sign = 0
        self._shake_reversals: list[float] = []
        self._shake_last = -math.inf

        self._flip_open = False
        self._flip_start = 0.0
        self._flip_angle = 0.0
        self._flip_face = 0
        self._flip_last = -math.inf

    def set_sensitivity(self, value: float) -> None:
        """Clamp and store the player's aim sensitivity (0.4..2.5)."""
        self._sensitivity = _clamp(
            float(value),
            config.AIM_SENSITIVITY_MIN,
            config.AIM_SENSITIVITY_MAX,
        )

    def reset(self) -> None:
        """Recenter: mark calibrated and clear buffers, windows and cooldowns."""
        self._calibrated = True
        self._last_t = None
        self._tilt_x = 0.0
        self._tilt_y = 0.0
        self._aim_x = 0.5
        self._aim_y = 0.5
        self._flick_armed = True
        self._flick_open_t = None
        self._flick_peak = 0.0
        self._flick_peak_vec = (0.0, 0.0)
        self._flick_last = -math.inf
        self._swing_open = False
        self._swing_travel = 0.0
        self._swing_peak_rate = 0.0
        self._swing_peak_vec = (0.0, 0.0)
        self._swing_last = -math.inf
        self._twist_open = False
        self._twist_angle = 0.0
        self._twist_last = -math.inf
        self._shake_sign = 0
        self._shake_reversals.clear()
        self._shake_last = -math.inf
        self._flip_open = False
        self._flip_angle = 0.0
        self._flip_face = 0
        self._flip_last = -math.inf

    def update(
        self, frame: ControllerFrame
    ) -> tuple[dict[str, float], list[Gesture]]:
        """Feed one frame; return posture axes to merge and the events fired."""
        events: list[Gesture] = []
        t = frame.timestamp
        dt = 0.0
        if self._last_t is not None:
            dt = min(max(t - self._last_t, 0.0), 0.05)
        self._last_t = t

        angle = frame.screen_angle if frame.screen_angle in _SCREEN_ANGLES else 0

        postures = self._tilt(frame, angle, dt)
        postures.update(self._aim(frame, angle, dt))

        lx, ly = rotate_screen(frame.linear_accel[0], frame.linear_accel[1], angle)
        events.extend(self._flick(lx, ly, t))

        gx, gy = rotate_screen(
            math.degrees(frame.gyro[1]), math.degrees(frame.gyro[2]), angle
        )
        events.extend(self._swing(gx, gy, t, dt))
        events.extend(self._twist(frame, t, dt))
        events.extend(self._shake(gx, gy, t))
        events.extend(self._flip(gx, gy, frame, t, dt))

        return postures, events

    # -- postures -----------------------------------------------------------

    def _tilt(
        self, frame: ControllerFrame, angle: int, dt: float
    ) -> dict[str, float]:
        if not self._calibrated:
            return {"tilt_x": 0.0, "tilt_y": 0.0}
        # orientation is already relative to the neutral pose: (alpha, beta, gamma).
        tx, ty = rotate_screen(frame.orientation[2], frame.orientation[1], angle)
        alpha = 1.0 if dt <= 0.0 else 1.0 - math.exp(-dt / config.TILT_SMOOTH_TAU)
        self._tilt_x += (tx - self._tilt_x) * alpha
        self._tilt_y += (ty - self._tilt_y) * alpha
        x = _deadzone(self._tilt_x, config.TILT_DEADZONE)
        y = _deadzone(self._tilt_y, config.TILT_DEADZONE)
        if abs(x) < config.TILT_CUTOFF:
            x = 0.0
        if abs(y) < config.TILT_CUTOFF:
            y = 0.0
        tilt_x = _clamp(x / config.TILT_SATURATION)
        tilt_y = _clamp(y / config.TILT_SATURATION)
        steer_mag = min(
            1.0, abs(tilt_x) * (config.TILT_SATURATION / config.STEER_SATURATION)
        )
        steer = 0.0 if tilt_x == 0.0 else (1.0 if tilt_x > 0 else -1.0) * (
            steer_mag ** config.STEER_EXPO
        )
        return {"tilt_x": tilt_x, "tilt_y": tilt_y, "steer": steer}

    def _aim(
        self, frame: ControllerFrame, angle: int, dt: float
    ) -> dict[str, float]:
        # gyro[1] is beta (pitch), gyro[2] is gamma (yaw); rotate to screen axes.
        gx, gy = rotate_screen(
            math.degrees(frame.gyro[1]), math.degrees(frame.gyro[2]), angle
        )
        yaw = _deadzone(gy, config.AIM_DEADZONE)
        pitch = _deadzone(gx, config.AIM_DEADZONE)
        self._aim_x += (yaw / config.AIM_FOV) * dt * self._sensitivity
        self._aim_y -= (pitch / config.AIM_FOV) * dt * self._sensitivity
        self._aim_x = _clamp(self._aim_x, 0.0, 1.0)
        self._aim_y = _clamp(self._aim_y, 0.0, 1.0)
        return {"aim_x": self._aim_x, "aim_y": self._aim_y}

    def _tilt_degrees(self) -> float:
        return math.hypot(self._tilt_x, self._tilt_y)

    # -- flick --------------------------------------------------------------

    def _flick(self, lx: float, ly: float, t: float) -> list[Gesture]:
        events: list[Gesture] = []
        magnitude = math.hypot(lx, ly)

        if self._flick_open_t is not None:
            if magnitude > self._flick_peak:
                self._flick_peak = magnitude
                self._flick_peak_vec = (lx, ly)
            if t - self._flick_open_t >= config.FLICK_WINDOW:
                event = self._close_flick(t)
                if event is not None:
                    events.append(event)
            return events

        if t - self._flick_last < config.FLICK_COOLDOWN:
            return events

        if magnitude < config.FLICK_RELEASE:
            self._flick_armed = True
            return events

        if self._flick_armed and magnitude >= config.FLICK_START:
            self._flick_open_t = t
            self._flick_peak = magnitude
            self._flick_peak_vec = (lx, ly)
            self._flick_armed = False
        return events

    def _close_flick(self, t: float) -> Gesture | None:
        self._flick_open_t = None
        peak = self._flick_peak
        vx, vy = self._flick_peak_vec
        self._flick_peak = 0.0
        self._flick_peak_vec = (0.0, 0.0)

        ax, ay = abs(vx), abs(vy)
        primary = max(ax, ay)
        if peak < config.FLICK_START or primary <= 0.0:
            return None
        if min(ax, ay) / primary > config.FLICK_AMBIGUITY:
            return None
        self._flick_last = t
        intensity = (peak - config.FLICK_START) / (config.FLICK_MAX - config.FLICK_START)
        direction = (
            ("right" if vx > 0 else "left")
            if ax >= ay
            else ("up" if vy > 0 else "down")
        )
        return self._make("flick", direction, intensity, t)

    # -- swing --------------------------------------------------------------

    def _swing(self, gx: float, gy: float, t: float, dt: float) -> list[Gesture]:
        events: list[Gesture] = []
        magnitude = math.hypot(gx, gy)

        if self._swing_open:
            self._swing_travel += magnitude * dt
            if magnitude > self._swing_peak_rate:
                self._swing_peak_rate = magnitude
                self._swing_peak_vec = (gx, gy)
            if magnitude < config.SWING_END:
                self._swing_open = False
                event = self._close_swing(t)
                if event is not None:
                    events.append(event)
            return events

        if t - self._swing_last < config.SWING_COOLDOWN:
            return events

        if magnitude >= config.SWING_START:
            self._swing_open = True
            self._swing_start = t
            self._swing_travel = magnitude * dt
            self._swing_peak_rate = magnitude
            self._swing_peak_vec = (gx, gy)
        return events

    def _close_swing(self, t: float) -> Gesture | None:
        duration = t - self._swing_start
        travel = self._swing_travel
        px, py = self._swing_peak_vec
        self._swing_travel = 0.0
        self._swing_peak_rate = 0.0
        self._swing_peak_vec = (0.0, 0.0)

        if duration < config.SWING_MIN or travel <= 0.0:
            return None
        self._swing_last = t
        direction = (
            ("up" if px > 0 else "down")
            if abs(px) >= abs(py)
            else ("right" if py > 0 else "left")
        )
        return self._make("swing", direction, travel / config.SWING_INTENSITY, t)

    # -- twist --------------------------------------------------------------

    def _twist(self, frame: ControllerFrame, t: float, dt: float) -> list[Gesture]:
        events: list[Gesture] = []
        roll = math.degrees(frame.gyro[0])

        if self._twist_open:
            self._twist_angle += roll * dt
            if self._tilt_degrees() > 35.0:
                self._twist_open = False
                self._twist_angle = 0.0
                return events
            if t - self._twist_start > config.TWIST_WINDOW:
                self._twist_open = False
                self._twist_angle = 0.0
                return events
            if abs(self._twist_angle) >= config.TWIST_ANGLE:
                self._twist_open = False
                angle = self._twist_angle
                self._twist_angle = 0.0
                self._twist_last = t
                direction = "cw" if angle > 0 else "ccw"
                events.append(
                    self._make("twist", direction, abs(angle) / config.TWIST_INTENSITY, t)
                )
            return events

        if t - self._twist_last < config.TWIST_COOLDOWN:
            return events
        if abs(roll) > config.TWIST_START:
            self._twist_open = True
            self._twist_start = t
            self._twist_angle = roll * dt
        return events

    # -- shake --------------------------------------------------------------

    def _shake(self, gx: float, gy: float, t: float) -> list[Gesture]:
        events: list[Gesture] = []
        dom = gx if abs(gx) >= abs(gy) else gy
        sign = 0 if abs(dom) < config.SHAKE_RATE else (1 if dom > 0 else -1)

        if sign != 0 and sign != self._shake_sign:
            if self._shake_sign != 0:
                self._shake_reversals.append(t)
                self._shake_reversals = [
                    x for x in self._shake_reversals if t - x <= config.SHAKE_WINDOW
                ]
            self._shake_sign = sign

        if t - self._shake_last >= config.SHAKE_COOLDOWN and len(
            self._shake_reversals
        ) >= config.SHAKE_REVERSALS:
            count = len(self._shake_reversals)
            self._shake_reversals.clear()
            self._shake_last = t
            events.append(self._make("shake", "none", count / 6.0, t))
        return events

    # -- flip ---------------------------------------------------------------

    def _flip(
        self, gx: float, gy: float, frame: ControllerFrame, t: float, dt: float
    ) -> list[Gesture]:
        events: list[Gesture] = []
        # A flip turns the phone over, so it is rotation about a horizontal
        # (pitch/yaw) axis, not about the screen normal (roll, which is twist).
        rate = math.hypot(gx, gy)

        if self._flip_open:
            self._flip_angle += rate * dt
            if self._tilt_degrees() > 35.0 or t - self._flip_start > config.FLIP_WINDOW:
                self._flip_open = False
                self._flip_angle = 0.0
                self._flip_face = 0
                return events
            face = self._face_sign(frame.accel[2])
            if self._flip_angle >= config.FLIP_ANGLE and face != 0 and face != self._flip_face:
                self._flip_open = False
                angle = self._flip_angle
                self._flip_angle = 0.0
                self._flip_last = t
                direction = "up" if face > 0 else "down"
                events.append(
                    self._make("flip", direction, angle / config.FLIP_INTENSITY, t)
                )
            return events

        if t - self._flip_last < config.FLIP_COOLDOWN:
            return events
        if rate > config.TWIST_START:
            self._flip_open = True
            self._flip_start = t
            self._flip_angle = rate * dt
            self._flip_face = self._face_sign(frame.accel[2])
        return events

    @staticmethod
    def _face_sign(accel_z: float) -> int:
        # Gravity along the screen normal: face up is positive, face down negative.
        if accel_z > 3.0:
            return 1
        if accel_z < -3.0:
            return -1
        return 0

    # -- shared -------------------------------------------------------------

    def _make(
        self, name: str, direction: str, intensity: float, t: float
    ) -> Gesture:
        return Gesture(
            slot=self._slot,
            controller_id=self._controller_id,
            name=name,
            direction=direction,
            intensity=_clamp(intensity, 0.0, 1.0),
            timestamp=t,
        )
