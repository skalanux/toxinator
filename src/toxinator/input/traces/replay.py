"""Replay a recorded trace as a ``ControllerSource``, re-running recognition."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from toxinator.api.input import ControllerFrame, ControllerInfo
from toxinator.input.gestures.recognizer import GestureRecognizer
from toxinator.input.source import SourceUpdate
from toxinator.input.traces.trace import Trace

REPLAY_CAPABILITIES: frozenset[str] = frozenset(
    {"buttons", "axes", "motion", "gyro", "gestures", "pointer", "touch", "screen"}
)


class ReplaySource:
    """Emit a trace's frames on the game clock, no phone and no wall sleeps.

    One ``GestureRecognizer`` runs per ``controller_id`` on the raw sensor fields
    of each frame, so replay reproduces the same detection as the recording. The
    emitted frame keeps the trace-relative timestamp for recognition (so ``dt``
    is exact) but is re-stamped to ``now`` so the hub's staleness logic works.
    """

    name = "replay"

    def __init__(
        self,
        trace: Trace,
        *,
        speed: float = 1.0,
        loop: bool = False,
    ) -> None:
        self._trace = trace
        self._speed = max(speed, 1e-6)
        self._loop = loop
        self._frames = sorted(trace.frames, key=lambda frame: frame.timestamp)
        self._duration = max((f.timestamp for f in self._frames), default=0.0)
        self._infos = self._build_infos()
        self._recognizers: dict[str, GestureRecognizer] = {}
        self._started_at: float | None = None
        self._index = 0
        self._started = False

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        self._started = True
        self._reset()

    def stop(self) -> None:
        self._started = False

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def speed(self) -> float:
        return self._speed

    def _build_infos(self) -> dict[str, ControllerInfo]:
        infos: dict[str, ControllerInfo] = {}
        for controller in self._trace.meta.controllers:
            controller_id = controller["id"]
            capabilities = frozenset(
                controller.get("capabilities", ()) or REPLAY_CAPABILITIES
            )
            try:
                slot = int(controller.get("slot", 0))
            except (TypeError, ValueError):
                slot = 0
            infos[controller_id] = ControllerInfo(
                id=controller_id,
                source="replay",
                capabilities=capabilities,
                slot=slot,
                connected=True,
                display_name=str(controller.get("display_name", controller_id)),
            )
        return infos

    def _reset(self) -> None:
        self._started_at = None
        self._index = 0
        self._recognizers = {}
        for controller_id, info in self._infos.items():
            recognizer = GestureRecognizer(info.slot, controller_id)
            # The recorded orientation is already relative to the neutral pose,
            # so mark calibrated so tilt/steer replay too.
            recognizer.reset()
            self._recognizers[controller_id] = recognizer

    # -- polling ------------------------------------------------------------

    def poll(self, now: float) -> Sequence[SourceUpdate]:
        if not self._started or not self._frames:
            return []
        if self._started_at is None:
            self._started_at = now

        # On loop, wrap the anchor forward one duration at a time and restart
        # recognition (cooldowns must not leak across the loop boundary).
        if self._loop and self._duration > 0.0:
            whole = int((now - self._started_at) * self._speed / self._duration)
            if whole > 0:
                self._started_at = now
                self._index = 0
                self._reset_recognizers()

        elapsed = (now - self._started_at) * self._speed
        updates: list[SourceUpdate] = []
        while self._index < len(self._frames):
            frame = self._frames[self._index]
            if frame.timestamp > elapsed:
                break
            self._index += 1
            updates.append(self._recognize(frame, now))
        return updates

    def _reset_recognizers(self) -> None:
        for controller_id, info in self._infos.items():
            self._recognizers[controller_id] = GestureRecognizer(info.slot, controller_id)
            self._recognizers[controller_id].reset()

    def _recognize(self, frame: ControllerFrame, now: float) -> SourceUpdate:
        controller_id = frame.controller_id
        recognizer = self._recognizers.get(controller_id)
        if recognizer is None:
            info = self._infos.get(
                controller_id,
                ControllerInfo(
                    id=controller_id,
                    source="replay",
                    capabilities=REPLAY_CAPABILITIES,
                    slot=0,
                    connected=True,
                ),
            )
            recognizer = GestureRecognizer(info.slot, controller_id)
            recognizer.reset()
            self._recognizers[controller_id] = recognizer
            self._infos[controller_id] = info

        postures, events = recognizer.update(frame)
        emitted = replace(
            frame,
            axes={**frame.axes, **postures},
            timestamp=now,
        )
        return SourceUpdate(self._infos[controller_id], emitted, tuple(events))
