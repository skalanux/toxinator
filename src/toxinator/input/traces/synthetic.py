"""Deterministic synthetic gesture traces and the negative suite.

No hardware: the lab's fixtures and the negative suite are synthesized here at
60 Hz. Each positive generator returns ``(frames, expected)`` where ``expected``
is the gesture ground truth (peak/instant ``t``, name, direction and intensity
bucketed to 0.25). The negative generators return quiet frames that must not
fire any event.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from toxinator.api.input import ControllerFrame
from toxinator.input.traces.trace import (
    ExpectedEvent,
    Trace,
    TraceMeta,
    bucketed,
    expected_path_for,
    write_expected,
    write_trace,
)

DT = 1.0 / 60.0
CONTROLLER_ID = "phone-1"


def _frame(
    t: float,
    *,
    gyro: tuple[float, float, float] = (0.0, 0.0, 0.0),
    linear: tuple[float, float, float] = (0.0, 0.0, 0.0),
    accel: tuple[float, float, float] = (0.0, 0.0, 9.81),
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    screen: int = 0,
) -> ControllerFrame:
    return ControllerFrame(
        controller_id=CONTROLLER_ID,
        timestamp=t,
        gyro=gyro,
        linear_accel=linear,
        accel=accel,
        orientation=orientation,
        screen_angle=screen,
    )


def _times(count: int) -> list[float]:
    return [i * DT for i in range(count)]


def _gyro_deg(value: float, axis: int) -> tuple[float, float, float]:
    vector = [0.0, 0.0, 0.0]
    vector[axis] = math.radians(value)
    return (vector[0], vector[1], vector[2])


# -- positive gestures ------------------------------------------------------


def flick(
    direction: str, *, peak: float = 30.0, count: int = 16
) -> tuple[list[ControllerFrame], list[ExpectedEvent]]:
    """Linear-accel spike on one axis: ``up``/``down``/``left``/``right``."""
    axis = 1 if direction in ("up", "down") else 0
    sign = 1.0 if direction in ("up", "right") else -1.0
    frames: list[ControllerFrame] = []
    for t in _times(count):
        magnitude = peak if 1 <= int(round(t / DT)) <= 10 else 0.0
        linear = [0.0, 0.0, 0.0]
        linear[axis] = sign * magnitude
        frames.append(_frame(t, linear=(linear[0], linear[1], linear[2])))
    intensity = bucketed((peak - 11.8) / (34.4 - 11.8))
    expected = [ExpectedEvent(t=DT, name="flick", direction=direction, intensity=intensity)]
    return frames, expected


def swing(
    direction: str, *, rate: float = 300.0, samples: int = 18
) -> tuple[list[ControllerFrame], list[ExpectedEvent]]:
    """Sustained gyro arc on one axis, then a drop below ``SWING_END``."""
    axis = 1 if direction in ("up", "down") else 2
    sign = 1.0 if direction in ("up", "right") else -1.0
    frames: list[ControllerFrame] = []
    for t in _times(samples + 2):
        index = int(round(t / DT))
        gyro = _gyro_deg(sign * rate, axis) if 1 <= index <= samples else (0.0, 0.0, 0.0)
        frames.append(_frame(t, gyro=gyro))
    travel = rate * DT * samples
    intensity = bucketed(travel / 360.0)
    expected = [ExpectedEvent(t=DT, name="swing", direction=direction, intensity=intensity)]
    return frames, expected


def twist(
    direction: str = "cw", *, rate: float = 100.0, samples: int = 24
) -> tuple[list[ControllerFrame], list[ExpectedEvent]]:
    """Sustained roll (gyro alpha) until the accumulated angle crosses 40 deg."""
    sign = 1.0 if direction == "cw" else -1.0
    frames: list[ControllerFrame] = []
    for t in _times(samples + 2):
        index = int(round(t / DT))
        gyro = _gyro_deg(sign * rate, 0) if 1 <= index <= samples else (0.0, 0.0, 0.0)
        frames.append(_frame(t, gyro=gyro))
    angle = rate * DT * samples
    intensity = bucketed(angle / 120.0)
    expected = [
        ExpectedEvent(
            t=samples * DT, name="twist", direction=direction, intensity=intensity
        )
    ]
    return frames, expected


def shake() -> tuple[list[ControllerFrame], list[ExpectedEvent]]:
    """Alternating yaw sign: three reversals fire one ``shake``."""
    frames: list[ControllerFrame] = [_frame(0.0)]
    signs = (1.0, -1.0, 1.0, -1.0)
    for i, sign in enumerate(signs, start=1):
        frames.append(_frame(i * DT, gyro=_gyro_deg(sign * 200.0, 2)))
    frames.append(_frame(5 * DT))
    expected = [ExpectedEvent(t=4 * DT, name="shake", direction="none", intensity=0.5)]
    return frames, expected


def flip(
    direction: str = "down", *, rate: float = 400.0, samples: int = 21
) -> tuple[list[ControllerFrame], list[ExpectedEvent]]:
    """Pitch over so gravity along the screen normal flips sign."""
    face_start = 9.81 if direction == "down" else -9.81
    face_end = -face_start
    flip_at = samples  # accel z changes sign just before the angle threshold
    frames: list[ControllerFrame] = []
    for t in _times(samples + 3):
        index = int(round(t / DT))
        accel_z = face_end if index >= flip_at else face_start
        gyro = _gyro_deg(rate, 1) if 1 <= index <= samples else (0.0, 0.0, 0.0)
        frames.append(_frame(t, gyro=gyro, accel=(0.0, 0.0, accel_z)))
    intensity = bucketed(rate * DT * samples / 180.0)
    expected = [
        ExpectedEvent(t=samples * DT, name="flip", direction=direction, intensity=intensity)
    ]
    return frames, expected


# -- aim drift --------------------------------------------------------------

_AIM_START = 0.5


def quiet_aim(
    seconds: float = 30.0, *, seed: int = 0, bias: float = 3.0, noise: float = 1.0
) -> list[ControllerFrame]:
    """Quiet phone: gyro noise plus a small yaw bias below the aim deadzone."""
    rng = random.Random(seed)
    frames: list[ControllerFrame] = []
    count = int(seconds / DT)
    for i in range(count):
        t = i * DT
        gyro = _deg3(
            rng.uniform(-noise, noise),
            rng.uniform(-noise, noise),
            bias + rng.uniform(-noise, noise),
        )
        frames.append(_frame(t, gyro=gyro))
    return frames


# -- negative suite ---------------------------------------------------------


def negative(
    kind: str, seconds: float, *, seed: int = 1
) -> list[ControllerFrame]:
    """Quiet/benign motion that must not fire any gesture event.

    Kinds: ``table`` (at rest), ``walking`` (2 Hz sway), ``hand_pass`` (slow
    transfer) and ``typing`` (small taps). All amplitudes stay below every
    detection threshold.
    """
    rng = random.Random(seed)
    count = int(seconds / DT)
    frames: list[ControllerFrame] = []
    for i in range(count):
        t = i * DT
        if kind == "table":
            accel = (rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), 9.81)
            gyro = _noise(rng, 1.0)
            linear = (rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1))
        elif kind == "walking":
            step = math.sin(2 * math.pi * 1.8 * t)
            accel = (1.5 * step, 1.0 * math.cos(2 * math.pi * 1.8 * t), 9.81)
            gyro = _deg3(25.0 * step, 18.0 * math.cos(2 * math.pi * 1.8 * t), 12.0 * step)
            linear = (0.8 * step, 0.6 * math.cos(2 * math.pi * 1.8 * t), 0.0)
        elif kind == "hand_pass":
            sway = math.sin(2 * math.pi * 0.5 * t)
            accel = (0.5 * sway, 0.5 * math.cos(2 * math.pi * 0.5 * t), 9.81)
            gyro = _deg3(20.0 * sway, 15.0 * sway, 8.0 * sway)
            linear = (0.3 * sway, 0.3 * sway, 0.0)
        else:  # typing
            tap = math.sin(2 * math.pi * 6.0 * t)
            accel = (1.5 * tap, 0.0, 9.81)
            gyro = _deg3(10.0 * tap, 8.0 * tap, 6.0 * tap)
            linear = (1.5 * tap, 0.0, 0.0)
        frames.append(_frame(t, gyro=gyro, accel=accel, linear=linear))
    return frames


def _noise(rng: random.Random, amplitude: float) -> tuple[float, float, float]:
    return _deg3(
        rng.uniform(-amplitude, amplitude),
        rng.uniform(-amplitude, amplitude),
        rng.uniform(-amplitude, amplitude),
    )


def _deg3(x: float, y: float, z: float) -> tuple[float, float, float]:
    return (math.radians(x), math.radians(y), math.radians(z))


# -- fixtures ---------------------------------------------------------------

_GESTURE_CONTROLLER = {
    "id": CONTROLLER_ID,
    "source": "phone",
    "capabilities": [
        "buttons",
        "axes",
        "motion",
        "gyro",
        "gestures",
        "pointer",
        "touch",
        "screen",
    ],
    "slot": 0,
    "display_name": "Celular P1",
}


def make_trace(
    frames: list[ControllerFrame], *, game: str = "gestures", seed: int | None = None
) -> Trace:
    return Trace(
        meta=TraceMeta(game=game, controllers=(_GESTURE_CONTROLLER,), seed=seed),
        frames=frames,
    )


def write_fixture(
    root: Path,
    name: str,
    frames: list[ControllerFrame],
    expected: list[ExpectedEvent],
) -> Path:
    trace = make_trace(frames)
    trace_path = root / f"{name}.jsonl"
    write_trace(trace_path, trace)
    write_expected(expected_path_for(trace_path), expected)
    return trace_path


def generate_fixtures(root: Path) -> list[Path]:
    """Write the committed positive, aim and short negative fixtures."""
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for direction in ("up", "down", "left", "right"):
        frames, expected = flick(direction)
        written.append(write_fixture(root, f"flick_{direction}", frames, expected))
    for direction in ("up", "down", "right", "left"):
        frames, expected = swing(direction)
        written.append(write_fixture(root, f"swing_{direction}", frames, expected))
    for direction in ("cw", "ccw"):
        frames, expected = twist(direction)
        written.append(write_fixture(root, f"twist_{direction}", frames, expected))
    frames, expected = shake()
    written.append(write_fixture(root, "shake", frames, expected))
    for direction in ("down", "up"):
        frames, expected = flip(direction)
        written.append(write_fixture(root, f"flip_{direction}", frames, expected))
    frames = quiet_aim(30.0)
    written.append(write_fixture(root, "aim_quiet_30s", frames, []))
    for kind in ("table", "walking", "hand_pass", "typing"):
        frames = negative(kind, 10.0)
        written.append(write_fixture(root, f"neg_{kind}", frames, []))
    return written
