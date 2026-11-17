"""Input hub: sources in, one normalized ``InputState`` out per frame."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import replace
from types import MappingProxyType

from toxinator.api.input import ControllerFrame, ControllerInfo, InputEvent, InputState
from toxinator.input.source import ControllerSource

logger = logging.getLogger(__name__)


class InputHub:
    """Poll controller sources and publish slots with stale/grace windows."""

    STALE_SECONDS = 0.2
    DISCONNECT_SECONDS = 2.0
    GRACE_SECONDS = 30.0

    def __init__(self, sources: Sequence[ControllerSource] | None = None) -> None:
        self._sources: list[ControllerSource] = list(sources or ())
        self._frames: dict[int, ControllerFrame] = {}
        self._infos: dict[int, ControllerInfo] = {}
        self._last_seen: dict[int, float] = {}
        self._listeners: list[Callable[[InputEvent], None]] = []
        self._started = False

    def add_source(self, source: ControllerSource) -> None:
        if self._started:
            source.start()
        self._sources.append(source)

    def subscribe(self, listener: Callable[[InputEvent], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def start(self) -> None:
        if self._started:
            return
        for source in self._sources:
            source.start()
        self._started = True

    def stop(self) -> None:
        for source in reversed(self._sources):
            source.stop()
        self._started = False

    def poll(self, now: float | None = None) -> InputState:
        timestamp = time.monotonic() if now is None else now

        for source in self._sources:
            try:
                updates = source.poll(timestamp)
            except Exception:
                logger.exception("controller source %r failed", source.name)
                continue
            for update in updates:
                self._apply_update(update.info, update.frame, timestamp)

        self._expire(timestamp)

        return InputState(
            timestamp=timestamp,
            frames=MappingProxyType(dict(self._frames)),
            controllers=MappingProxyType(dict(self._infos)),
        )

    def _apply_update(
        self,
        info: ControllerInfo,
        frame: ControllerFrame | None,
        now: float,
    ) -> None:
        slot = info.slot
        previous = self._infos.get(slot)

        if frame is not None:
            if not info.connected:
                info = replace(info, connected=True)
            self._frames[slot] = frame
            self._last_seen[slot] = now
            if previous is None or not previous.connected:
                self._emit("join", info, now)
        self._infos[slot] = info

    def _expire(self, now: float) -> None:
        for slot in list(self._infos):
            info = self._infos[slot]
            last_seen = self._last_seen.get(slot, 0.0)
            age = now - last_seen

            if age > self.STALE_SECONDS:
                self._frames.pop(slot, None)

            if info.connected and age > self.DISCONNECT_SECONDS:
                info = replace(info, connected=False)
                self._infos[slot] = info
                self._emit("disconnect", info, now)

            if age > self.GRACE_SECONDS:
                self._frames.pop(slot, None)
                self._infos.pop(slot, None)
                self._last_seen.pop(slot, None)
                self._emit("leave", info, now)

    def _emit(self, kind: str, info: ControllerInfo, now: float) -> None:
        event = InputEvent(
            kind=kind,
            slot=info.slot,
            controller_id=info.id,
            timestamp=now,
        )
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:
                logger.exception("input event listener failed")
