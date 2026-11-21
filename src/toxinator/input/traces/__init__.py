"""Trace recording, replay and synthetic generation for the gestures lab."""

from toxinator.input.traces.metrics import GestureResult, evaluate, false_positives, recognize
from toxinator.input.traces.recorder import TraceRecorder
from toxinator.input.traces.replay import ReplaySource
from toxinator.input.traces.trace import (
    ExpectedEvent,
    Trace,
    TraceEvent,
    TraceMeta,
    bucketed,
    expected_path_for,
    read_expected,
    read_trace,
    write_expected,
    write_trace,
)

__all__ = [
    "ExpectedEvent",
    "GestureResult",
    "ReplaySource",
    "Trace",
    "TraceEvent",
    "TraceMeta",
    "TraceRecorder",
    "bucketed",
    "evaluate",
    "expected_path_for",
    "false_positives",
    "read_expected",
    "read_trace",
    "recognize",
    "write_expected",
    "write_trace",
]
