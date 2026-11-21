"""Controller source backed by the phone WebSocket registry."""

from __future__ import annotations

from collections.abc import Sequence

from toxinator.api.input import ControllerInfo
from toxinator.input.phone.registry import PHONE_CAPABILITIES, PhoneRegistry
from toxinator.input.source import SourceUpdate

STALE_SECONDS = 0.2


class PhoneSource:
    name = "phone"

    def __init__(self, registry: PhoneRegistry) -> None:
        self._registry = registry

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def poll(self, now: float) -> Sequence[SourceUpdate]:
        updates: list[SourceUpdate] = []
        for connection in self._registry.snapshot():
            gestures = self._registry.take_gestures(connection.slot)
            frame = connection.frame
            if not connection.connected or frame is None:
                continue
            if now - frame.timestamp > STALE_SECONDS:
                continue
            info = ControllerInfo(
                id=connection.controller_id,
                source="phone",
                capabilities=PHONE_CAPABILITIES,
                slot=connection.slot,
                connected=True,
                display_name=f"Celular P{connection.slot + 1}",
            )
            updates.append(SourceUpdate(info, frame, tuple(gestures)))
        return updates
