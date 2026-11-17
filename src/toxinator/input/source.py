"""Controller source protocol shared by the hub."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from toxinator.api.input import ControllerFrame, ControllerInfo


@dataclass(frozen=True, slots=True)
class SourceUpdate:
    """One source update: identity always, frame only while fresh."""

    info: ControllerInfo
    frame: ControllerFrame | None = None


class ControllerSource(Protocol):
    """A pollable source of controller updates.

    Sources run their own transport (if any) and expose a thread-safe
    ``poll`` that the main loop calls once per frame.
    """

    name: str

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def poll(self, now: float) -> Sequence[SourceUpdate]: ...
