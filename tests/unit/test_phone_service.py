"""Phone feedback service."""

from __future__ import annotations

from toxinator.api.phone import NullPhoneService


def test_null_phone_service_is_a_safe_noop() -> None:
    phone = NullPhoneService()
    phone.vibrate([20, 30], slot=0)
    phone.tone(880, 80, volume=0.2, slot=1)
    phone.stop()
    phone.stop(slot=0)
