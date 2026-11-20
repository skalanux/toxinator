"""Thread-safe registry of connected phones and their slots."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from typing import Any

from toxinator.api.input import ControllerFrame
from toxinator.input.phone.protocol import Vec3, build_frame, vec3

PHONE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "buttons",
        "axes",
        "motion",
        "gyro",
        "pointer",
        "touch",
        "haptics",
        "camera",
        "panel",
        "speaker",
    }
)


@dataclass
class PhoneConnection:
    slot: int
    controller_id: str
    remote: str
    name: str
    connected: bool = True
    last_seen: float = 0.0
    frame_timestamp: float = 0.0
    frame: ControllerFrame | None = None
    neutral: Vec3 | None = None
    raw_orientation: Vec3 = (0.0, 0.0, 0.0)
    last_payload: dict[str, Any] | None = None


class PhoneRegistry:
    """Assign slots to phones and hold their latest state.

    The WebSocket server runs in its own thread and writes here; the input
    hub reads from the main thread. All public methods take the lock.
    """

    def __init__(self, max_slots: int = 4) -> None:
        self._max_slots = max_slots
        self._lock = threading.RLock()
        self._connections: dict[int, PhoneConnection] = {}

    @property
    def max_slots(self) -> int:
        return self._max_slots

    def join(
        self,
        *,
        remote: str = "",
        name: str = "",
        now: float | None = None,
    ) -> PhoneConnection | None:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            for slot in range(self._max_slots):
                if slot not in self._connections:
                    connection = PhoneConnection(
                        slot=slot,
                        controller_id=f"phone-{slot + 1}",
                        remote=remote,
                        name=name,
                        last_seen=timestamp,
                    )
                    self._connections[slot] = connection
                    return replace(connection)
        return None

    def leave(self, slot: int) -> None:
        with self._lock:
            self._connections.pop(slot, None)

    def update_state(
        self,
        slot: int,
        payload: dict[str, Any],
        now: float | None = None,
    ) -> None:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            connection = self._connections.get(slot)
            if connection is None:
                return
            connection.last_seen = timestamp
            connection.frame_timestamp = timestamp
            connection.connected = True
            connection.raw_orientation = vec3(payload.get("orientation"))
            connection.last_payload = dict(payload)
            connection.frame = build_frame(
                payload,
                controller_id=connection.controller_id,
                timestamp=timestamp,
                neutral=connection.neutral,
            )

    def calibrate(self, slot: int) -> None:
        with self._lock:
            connection = self._connections.get(slot)
            if connection is None:
                return
            connection.neutral = connection.raw_orientation
            if connection.last_payload is not None:
                connection.frame = build_frame(
                    connection.last_payload,
                    controller_id=connection.controller_id,
                    timestamp=connection.frame_timestamp,
                    neutral=connection.neutral,
                )

    def snapshot(self) -> list[PhoneConnection]:
        with self._lock:
            return [replace(connection) for connection in self._connections.values()]

    def connected_count(self) -> int:
        with self._lock:
            return len(self._connections)
