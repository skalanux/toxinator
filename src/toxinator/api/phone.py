"""Phone feedback service: vibration and speaker tones."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class PhoneService(Protocol):
    """Optional feedback on the phone controller.

    ``slot=None`` broadcasts to every connected phone. Games should treat
    haptics and audio as optional: on iOS there is no web vibration, and audio
    needs a user gesture to unlock the browser audio context.
    """

    def vibrate(self, pattern: int | Sequence[int], slot: int | None = None) -> None:
        """Vibrate a phone. Values are milliseconds, alternating on/off."""
        ...

    def tone(
        self,
        frequency: float,
        duration_ms: int,
        *,
        volume: float = 0.35,
        slot: int | None = None,
    ) -> None:
        """Play a short sine tone on the phone speaker."""
        ...

    def stop(self, slot: int | None = None) -> None:
        """Stop tones and vibration on one phone or all phones."""
        ...

    def recenter(self, slot: int | None = None) -> None:
        """Recalibrate the neutral pose and reset the gyro pointer (aim)."""
        ...

    def panel(
        self,
        *,
        title: str = "",
        image: str | None = None,
        fit: str = "contain",
        slot: int | None = None,
    ) -> None:
        """Show a static image panel on the phone, or clear it with ``image=None``."""
        ...

    def clear_panel(self, *, slot: int | None = None) -> None:
        """Hide the phone panel."""
        ...


class NullPhoneService:
    """No-op implementation used when a game runs without a phone session."""

    def vibrate(self, pattern: int | Sequence[int], slot: int | None = None) -> None:
        return None

    def tone(
        self,
        frequency: float,
        duration_ms: int,
        *,
        volume: float = 0.35,
        slot: int | None = None,
    ) -> None:
        return None

    def stop(self, slot: int | None = None) -> None:
        return None

    def recenter(self, slot: int | None = None) -> None:
        return None

    def panel(
        self,
        *,
        title: str = "",
        image: str | None = None,
        fit: str = "contain",
        slot: int | None = None,
    ) -> None:
        return None

    def clear_panel(self, *, slot: int | None = None) -> None:
        return None
