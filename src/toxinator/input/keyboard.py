"""Keyboard/mouse simulator source for the console and games."""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

from toxinator.api.input import ControllerFrame, ControllerInfo, Gesture, TouchPoint
from toxinator.input.source import SourceUpdate

KEY_BUTTONS: Mapping[str, str] = MappingProxyType(
    {
        "enter": "cross",
        "j": "cross",
        "escape": "circle",
        "k": "circle",
        "l": "square",
        "i": "triangle",
        "tab": "options",
        "q": "l1",
        "e": "r1",
    }
)

ARROW_STICK: Mapping[str, tuple[float, float]] = MappingProxyType(
    {
        "arrow_left": (-1.0, 0.0),
        "arrow_right": (1.0, 0.0),
        "arrow_up": (0.0, 1.0),
        "arrow_down": (0.0, -1.0),
    }
)

WASD_STICK: Mapping[str, tuple[float, float]] = MappingProxyType(
    {
        "a": (-1.0, 0.0),
        "d": (1.0, 0.0),
        "w": (0.0, 1.0),
        "s": (0.0, -1.0),
    }
)

MOUSE_BUTTONS: Mapping[str, str] = MappingProxyType({"mouse1": "cross", "mouse3": "circle"})

GESTURE_KEYS: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "f": ("flick", "up"),
        "g": ("swing", "right"),
        "t": ("twist", "cw"),
        "h": ("shake", "none"),
        "v": ("flip", "down"),
    }
)
GESTURE_INTENSITY = 0.8

KEYBOARD_CAPABILITIES: frozenset[str] = frozenset(
    {"buttons", "axes", "pointer", "touch", "gestures"}
)


class KeyboardMouseState:
    """Thread-safe snapshot of held keys and mouse state, no Panda3D required."""

    def __init__(self, *, wasd: bool = True) -> None:
        self._lock = threading.RLock()
        self._keys: set[str] = set()
        self._mouse_buttons: set[str] = set()
        self._mouse_x = 0.5
        self._mouse_y = 0.5
        self._mouse_inside = False
        self._wasd = wasd

    def set_wasd(self, enabled: bool) -> None:
        with self._lock:
            self._wasd = enabled

    def press(self, key: str) -> None:
        with self._lock:
            self._keys.add(key)

    def release(self, key: str) -> None:
        with self._lock:
            self._keys.discard(key)

    def press_mouse(self, button: str) -> None:
        with self._lock:
            self._mouse_buttons.add(button)

    def release_mouse(self, button: str) -> None:
        with self._lock:
            self._mouse_buttons.discard(button)

    def set_pointer(self, x: float, y: float, *, inside: bool = True) -> None:
        with self._lock:
            self._mouse_x = max(0.0, min(1.0, x))
            self._mouse_y = max(0.0, min(1.0, y))
            self._mouse_inside = inside

    def clear(self) -> None:
        with self._lock:
            self._keys.clear()
            self._mouse_buttons.clear()

    def held_keys(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._keys)

    def snapshot(self) -> tuple[frozenset[str], tuple[float, float], tuple[float, float] | None]:
        with self._lock:
            buttons = {KEY_BUTTONS[key] for key in self._keys if key in KEY_BUTTONS}
            stick = dict(ARROW_STICK)
            if self._wasd:
                stick.update(WASD_STICK)
            dx = sum(vector[0] for key, vector in stick.items() if key in self._keys)
            dy = sum(vector[1] for key, vector in stick.items() if key in self._keys)
            length = (dx * dx + dy * dy) ** 0.5
            if length > 1.0:
                dx /= length
                dy /= length
            buttons.update(
                MOUSE_BUTTONS[button] for button in self._mouse_buttons if button in MOUSE_BUTTONS
            )
            pointer = (self._mouse_x, self._mouse_y) if self._mouse_inside else None
            return frozenset(buttons), (dx, dy), pointer


class KeyboardMouseSource:
    """A ``ControllerSource`` that turns keyboard/mouse into a controller.

    ``attach`` binds the Panda3D events in the app's main thread; ``poll`` and
    the pure ``state`` are usable without Panda3D in tests.
    """

    name = "keyboard"

    def __init__(self, slot: int = 4, *, wasd: bool = True) -> None:
        self.slot = slot
        self.state = KeyboardMouseState(wasd=wasd)
        self._base: Any | None = None
        self._bindings: list[str] = []
        self._prev_gesture_keys: frozenset[str] = frozenset()
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False
        self.detach()

    def attach(self, base: Any) -> None:
        if self._base is not None:
            return
        self._base = base
        for key in (*KEY_BUTTONS, *ARROW_STICK, *WASD_STICK, *GESTURE_KEYS):
            self._bind(base, key, self.state.press, [key])
            self._bind(base, f"{key}-up", self.state.release, [key])
        for button in MOUSE_BUTTONS:
            self._bind(base, button, self.state.press_mouse, [button])
            self._bind(base, f"{button}-up", self.state.release_mouse, [button])

    def detach(self) -> None:
        base = self._base
        if base is None:
            return
        for event in self._bindings:
            try:
                base.ignore(event)
            except Exception:
                continue
        self._bindings.clear()
        self._base = None
        self._prev_gesture_keys = frozenset()
        self.state.clear()

    def _bind(self, base: Any, event: str, func: Any, args: list[Any]) -> None:
        try:
            base.accept(event, func, args)
        except Exception:
            return
        self._bindings.append(event)

    def poll(self, now: float) -> Sequence[SourceUpdate]:
        if not self._started:
            return []
        self._read_mouse()
        buttons, move, pointer = self.state.snapshot()
        touches: tuple[TouchPoint, ...] = ()
        if pointer is not None and ({"cross", "circle"} & buttons):
            touches = (TouchPoint(0, pointer[0], pointer[1], 1.0),)
        frame = ControllerFrame(
            controller_id="keyboard-1",
            timestamp=now,
            buttons=buttons,
            axes={"move_x": move[0], "move_y": move[1]},
            pointer=pointer,
            touch=touches,
        )
        gestures = self._gesture_events(now)
        info = ControllerInfo(
            id="keyboard-1",
            source="sim",
            capabilities=KEYBOARD_CAPABILITIES,
            slot=self.slot,
            connected=True,
            display_name="Teclado",
        )
        return [SourceUpdate(info, frame, gestures)]

    def _gesture_events(self, now: float) -> tuple[Gesture, ...]:
        held = self.state.held_keys()
        pressed = held - self._prev_gesture_keys
        self._prev_gesture_keys = held
        events: list[Gesture] = []
        for key in sorted(pressed):
            gesture = GESTURE_KEYS.get(key)
            if gesture is None:
                continue
            name, direction = gesture
            events.append(
                Gesture(
                    slot=self.slot,
                    controller_id="keyboard-1",
                    name=name,
                    direction=direction,
                    intensity=GESTURE_INTENSITY,
                    timestamp=now,
                )
            )
        return tuple(events)

    def _read_mouse(self) -> None:
        base = self._base
        if base is None:
            return
        watcher = getattr(base, "mouseWatcherNode", None)
        if watcher is None:
            return
        try:
            inside = bool(watcher.hasMouse())
            if not inside:
                pointer = self.state.snapshot()[2]
                if pointer is not None:
                    self.state.set_pointer(pointer[0], pointer[1], inside=False)
                return
            self.state.set_pointer(
                (watcher.getMouseX() + 1.0) / 2.0,
                (1.0 - watcher.getMouseY()) / 2.0,
            )
        except Exception:
            return
