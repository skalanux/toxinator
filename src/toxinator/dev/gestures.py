"""``toxinator dev gestures``: tuning bench for the gesture recognizer.

Shows, per slot, the raw vs. filtered sensors (``accel``, ``linear``, ``gyro``
in deg/s), the postures (``tilt``/``steer``/``aim``) and the recognized events
with their intensity as confidence. Supports ``--record`` (trace + sidecar),
``--replay`` (no phone, with ``--loop``/``--speed``) and ``--trace`` (one line
per event).
"""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path

from toxinator.api.input import Gesture, InputState
from toxinator.dev.announce import announce_phone
from toxinator.dev.session import PhoneSession, start_phone_session
from toxinator.input.hub import InputHub
from toxinator.input.traces import ReplaySource, TraceRecorder, read_trace
from toxinator.input.traces.trace import expected_path_for

logger = logging.getLogger(__name__)


def _deg(rad_s: float) -> float:
    return math.degrees(rad_s)


def _vec(values: tuple[float, float, float], fmt: str = "+.1f") -> str:
    return " ".join(format(value, fmt) for value in values)


def _event_line(gesture: Gesture) -> str:
    return (
        f"t={gesture.timestamp:7.3f}  P{gesture.slot + 1}  "
        f"{gesture.name:<6} {gesture.direction:<5} {gesture.intensity:.2f}"
    )


def _slot_line(slot: int, state: InputState) -> str:
    frame = state.frame(slot)
    info = state.controller(slot)
    if frame is None:
        if info is not None:
            return f"P{slot + 1} {info.display_name or info.source}  gracia"
        return f"P{slot + 1} libre"

    accel = frame.accel
    linear = frame.linear_accel
    gyro = (_deg(frame.gyro[0]), _deg(frame.gyro[1]), _deg(frame.gyro[2]))
    tilt_x = frame.axis("tilt_x")
    tilt_y = frame.axis("tilt_y")
    steer = frame.axis("steer")
    aim_x = frame.axis("aim_x")
    aim_y = frame.axis("aim_y")
    events = " ".join(
        f"{g.name}:{g.direction}:{g.intensity:.2f}" for g in state.gestures_for(slot)
    )
    return (
        f"P{slot + 1}  "
        f"accel[{_vec(accel)}]  lin[{_vec(linear)}]  gyro[{_vec(gyro, '+.0f')}]  "
        f"tilt({tilt_x:+.2f},{tilt_y:+.2f}) steer{steer:+.2f}  "
        f"aim({aim_x:.2f},{aim_y:.2f})"
        + (f"  ev: {events}" if events else "")
    )


def run_gestures_lab(
    *,
    record: Path | None = None,
    replay: Path | None = None,
    loop: bool = False,
    speed: float = 1.0,
    trace_events: bool = False,
    host: str | None = None,
    port: int = 8443,
    token: str | None = None,
    demo: bool = False,
    seconds: float | None = None,
    https: bool = False,
    cert: Path | None = None,
    key: Path | None = None,
    cloudflare: bool = False,
    keyboard: bool = True,
    keyboard_slot: int = 4,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    session: PhoneSession | None = None
    recorder: TraceRecorder | None = None
    if replay is not None:
        trace = read_trace(replay)
        hub = InputHub([ReplaySource(trace, speed=speed, loop=loop)])
        hub.start()
        print(f"replay: {replay} ({len(trace.frames)} frames, {trace.duration:.2f}s)")
    else:
        session = start_phone_session(
            host=host,
            port=port,
            token=token,
            demo=demo,
            keyboard=keyboard,
            keyboard_slot=keyboard_slot,
            https=https,
            cert=cert,
            key=key,
            cloudflare=cloudflare,
        )
        session.set_mode("game")
        hub = session.hub
        announce_phone(session, demo=demo)

    if record is not None:
        recorder = TraceRecorder()
        recorder.start(record, game="gestures")

    deadline = time.monotonic() + seconds if seconds is not None else None
    last_print = 0.0
    try:
        while True:
            state = hub.poll()
            now = time.monotonic()

            if recorder is not None:
                for slot, info in state.controllers.items():
                    recorder.record_controller(info)
                    frame = state.frame(slot)
                    if frame is not None:
                        recorder.record_frame(frame)
                for gesture in state.gestures:
                    recorder.record_gesture(gesture)

            if trace_events:
                for gesture in sorted(state.gestures, key=lambda g: g.timestamp):
                    print(_event_line(gesture), flush=True)

            if now - last_print >= 0.5:
                print("\n".join(_slot_line(slot, state) for slot in range(4)), flush=True)
                last_print = now

            if deadline is not None and now >= deadline:
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        if recorder is not None:
            path = recorder.stop()
            if path is not None:
                print(f"trace:   {path}", flush=True)
                print(f"sidecar: {expected_path_for(path)}", flush=True)
        if session is not None:
            session.stop()
        else:
            hub.stop()
