from __future__ import annotations

from types import MappingProxyType

from toxinator.api.input import ControllerFrame, ControllerInfo, InputState
from toxinator.input.keyboard import KeyboardMouseSource, KeyboardMouseState


def test_keyboard_maps_canonical_buttons_and_stick() -> None:
    state = KeyboardMouseState()
    state.press("j")
    state.press("arrow_right")

    buttons, move, pointer = state.snapshot()

    assert buttons == frozenset({"cross"})
    assert move == (1.0, 0.0)
    assert pointer is None


def test_keyboard_releases_and_wasd_switch() -> None:
    state = KeyboardMouseState()
    state.press("d")
    assert state.snapshot()[1] == (1.0, 0.0)

    state.set_wasd(False)
    assert state.snapshot()[1] == (0.0, 0.0)

    state.press("q")
    state.press("e")
    state.press("tab")
    buttons = state.snapshot()[0]
    assert {"l1", "r1", "options"} <= buttons
    state.release("q")
    assert "l1" not in state.snapshot()[0]


def test_keyboard_mouse_pointer_and_touch() -> None:
    source = KeyboardMouseSource(slot=4)
    source.start()
    source.state.set_pointer(0.25, 0.75)
    source.state.press_mouse("mouse1")

    updates = source.poll(1.0)

    assert len(updates) == 1
    update = updates[0]
    assert update.info.source == "sim"
    assert update.info.slot == 4
    assert update.frame is not None
    assert update.frame.pointer == (0.25, 0.75)
    assert update.frame.button("cross")
    assert update.frame.touch[0].x == 0.25
    source.stop()


def test_primary_frame_prefers_phone() -> None:
    phone = ControllerFrame("phone-1", 1.0)
    keyboard = ControllerFrame("keyboard-1", 1.0)
    state = InputState(
        timestamp=1.0,
        frames=MappingProxyType({0: phone, 4: keyboard}),
        controllers=MappingProxyType(
            {
                0: ControllerInfo("phone-1", "phone", frozenset(), 0, True),
                4: ControllerInfo("keyboard-1", "sim", frozenset(), 4, True),
            }
        ),
    )

    assert state.primary_slot() == 0
    assert state.primary_frame() is phone
    info = state.primary_controller()
    assert info is not None
    assert info.source == "phone"


def test_primary_frame_falls_back_to_any_source() -> None:
    keyboard = ControllerFrame("keyboard-1", 1.0)
    state = InputState(
        timestamp=1.0,
        frames=MappingProxyType({4: keyboard}),
        controllers=MappingProxyType(
            {4: ControllerInfo("keyboard-1", "sim", frozenset(), 4, True)}
        ),
    )

    assert state.primary_slot() == 4
    assert state.primary_frame() is keyboard
