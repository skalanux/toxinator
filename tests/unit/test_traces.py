"""Trace format, recorder and replay source (milestone 3: lab)."""

from __future__ import annotations

from pathlib import Path

import pytest

from toxinator.api.input import ControllerFrame, ControllerInfo, Gesture, TouchPoint
from toxinator.input.traces.metrics import recognize
from toxinator.input.traces.recorder import TraceRecorder
from toxinator.input.traces.replay import ReplaySource
from toxinator.input.traces.trace import (
    ExpectedEvent,
    Trace,
    TraceMeta,
    bucketed,
    expected_path_for,
    frame_from_dict,
    frame_to_dict,
    read_expected,
    read_trace,
    write_expected,
    write_trace,
)


def test_bucketed_rounds_to_quarters() -> None:
    assert bucketed(0.0) == 0.0
    assert bucketed(0.13) == 0.25
    assert bucketed(0.47) == 0.5
    assert bucketed(0.74) == 0.75
    assert bucketed(0.95) == 1.0
    assert bucketed(1.5) == 1.0


def test_frame_round_trips_all_fields() -> None:
    frame = ControllerFrame(
        controller_id="phone-1",
        timestamp=1.5,
        buttons=frozenset({"cross", "circle"}),
        axes={"move_x": 0.5, "tilt_x": -0.25},
        accel=(0.1, -0.2, 9.81),
        gyro=(0.0, 0.01, -0.02),
        orientation=(10.0, 20.0, 30.0),
        pointer=(0.3, 0.7),
        touch=(TouchPoint(0, 0.5, 0.6, 0.9),),
        screen_angle=90,
        linear_accel=(1.0, 2.0, 3.0),
    )
    rebuilt = frame_from_dict(frame_to_dict(frame), controller_id="phone-1", t=1.5)
    assert rebuilt == frame


def test_trace_write_read_round_trip(tmp_path: Path) -> None:
    frames = [
        ControllerFrame(controller_id="phone-1", timestamp=0.0),
        ControllerFrame(controller_id="phone-1", timestamp=1.0 / 60.0),
    ]
    trace = Trace(
        meta=TraceMeta(game="gestures", controllers=({"id": "phone-1", "slot": 0},)),
        frames=frames,
    )
    path = tmp_path / "sample.jsonl"
    write_trace(path, trace)

    read = read_trace(path)
    assert read.meta.game == "gestures"
    assert read.duration == pytest.approx(1.0 / 60.0)
    assert [frame.timestamp for frame in read.frames] == [0.0, 1.0 / 60.0]


def test_read_trace_rejects_unknown_version(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"type": "meta", "trace_version": 99}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="trace_version"):
        read_trace(path)


def test_expected_sidecar_round_trip(tmp_path: Path) -> None:
    sidecar = tmp_path / "gesture.expected.json"
    events = [ExpectedEvent(t=0.5, name="flick", direction="up", intensity=0.75)]
    write_expected(sidecar, events)
    assert read_expected(sidecar) == events
    assert expected_path_for(tmp_path / "gesture.jsonl") == sidecar


def test_recorder_writes_trace_and_sidecar(tmp_path: Path) -> None:
    recorder = TraceRecorder()
    info = ControllerInfo(
        id="phone-1",
        source="phone",
        capabilities=frozenset({"gyro", "gestures"}),
        slot=0,
        connected=True,
    )
    recorder.start(tmp_path / "rec.jsonl", game="gestures", now=100.0)
    recorder.record_controller(info)
    recorder.record_frame(
        ControllerFrame(controller_id="phone-1", timestamp=100.0)
    )
    recorder.record_gesture(
        Gesture(
            slot=0, controller_id="phone-1", name="flick", direction="up",
            intensity=0.805, timestamp=100.2,
        )
    )
    path = recorder.stop()

    assert path is not None
    trace = read_trace(path)
    assert trace.meta.controllers[0]["id"] == "phone-1"
    assert trace.frames[0].timestamp == 0.0
    sidecar = read_expected(expected_path_for(path))
    assert len(sidecar) == 1
    assert sidecar[0].name == "flick"
    assert sidecar[0].direction == "up"
    assert sidecar[0].intensity == 0.75
    assert sidecar[0].t == pytest.approx(0.2)


def _replay_events(trace: Trace, *, speed: float = 1.0, loop: bool = False) -> list[Gesture]:
    source = ReplaySource(trace, speed=speed, loop=loop)
    source.start()
    events: list[Gesture] = []
    now = 0.0
    end = trace.duration + 0.02
    if loop:
        end = trace.duration * 3 + 0.02
    while now <= end:
        for update in source.poll(now):
            events.extend(update.gestures)
        now += 1.0 / 120.0
    return events


def test_replay_reproduces_recognizer_detection() -> None:
    from toxinator.input.traces import synthetic

    frames, _ = synthetic.swing("up")
    trace = synthetic.make_trace(frames)

    direct = recognize(trace)
    replayed = _replay_events(trace)

    def key(gesture: Gesture) -> tuple[str, str, float, float]:
        return (
            gesture.name,
            gesture.direction,
            round(gesture.intensity, 4),
            round(gesture.timestamp, 4),
        )

    assert [key(g) for g in replayed] == [key(g) for g in direct]


def test_replay_loops_and_repeats_detection() -> None:
    from toxinator.input.traces import synthetic

    frames, _ = synthetic.flick("up")
    trace = synthetic.make_trace(frames)

    single = _replay_events(trace)
    looped = _replay_events(trace, loop=True)
    # Three loops -> three times the events of a single pass.
    assert len(looped) == 3 * len(single)
