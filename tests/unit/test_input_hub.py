from __future__ import annotations

from collections.abc import Sequence

from toxinator.api.input import ControllerFrame, ControllerInfo
from toxinator.input.hub import InputHub
from toxinator.input.source import SourceUpdate


class FakeSource:
    name = "fake"

    def __init__(self) -> None:
        self.updates: list[SourceUpdate] = []
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def poll(self, now: float) -> Sequence[SourceUpdate]:
        return list(self.updates)


def info(connected: bool = True) -> ControllerInfo:
    return ControllerInfo(
        id="fake-1",
        source="fake",
        capabilities=frozenset({"buttons"}),
        slot=0,
        connected=connected,
        display_name="Fake",
    )


def frame(timestamp: float = 100.0) -> ControllerFrame:
    return ControllerFrame(controller_id="fake-1", timestamp=timestamp)


def test_hub_publishes_and_expires_slots() -> None:
    source = FakeSource()
    hub = InputHub([source])
    events: list[str] = []
    hub.subscribe(lambda event: events.append(event.kind))

    hub.start()
    assert source.started

    source.updates = [SourceUpdate(info(), frame(100.0))]
    state = hub.poll(now=100.0)
    assert state.frame(0) is not None
    assert state.controller(0) is not None
    assert state.connected_slots == (0,)
    assert events == ["join"]

    source.updates = []
    state = hub.poll(now=100.1)
    assert state.frame(0) is not None

    state = hub.poll(now=100.5)
    assert state.frame(0) is None
    controller = state.controller(0)
    assert controller is not None
    assert controller.connected is True

    state = hub.poll(now=103.0)
    controller = state.controller(0)
    assert controller is not None
    assert controller.connected is False
    assert "disconnect" in events

    state = hub.poll(now=131.0)
    assert state.controller(0) is None
    assert "leave" in events

    hub.stop()
    assert source.stopped


def test_hub_reconnects_after_disconnect() -> None:
    source = FakeSource()
    hub = InputHub([source])
    hub.start()

    source.updates = [SourceUpdate(info(), frame(100.0))]
    hub.poll(now=100.0)
    source.updates = []
    hub.poll(now=103.0)

    source.updates = [SourceUpdate(info(), frame(104.0))]
    state = hub.poll(now=104.0)
    assert state.frame(0) is not None
    controller = state.controller(0)
    assert controller is not None
    assert controller.connected is True
