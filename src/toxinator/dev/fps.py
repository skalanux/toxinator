"""Overlay de performance para medir FPS y frametime en hardware real.

Se activa con ``--fps`` en el launcher, ``toxinator play`` y
``toxinator dev phone``; **F3** lo oculta o lo vuelve a mostrar. Mide el último
segundo de frames, así que no necesita PStats ni instrumentar el juego.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import TextNode, Vec4

_GOOD = Vec4(0.62, 0.81, 0.42, 1.0)
_WARN = Vec4(0.88, 0.69, 0.41, 1.0)
_BAD = Vec4(0.97, 0.46, 0.56, 1.0)
_MUTED = Vec4(0.75, 0.79, 0.96, 1.0)
_CARD = Vec4(0.08, 0.08, 0.12, 0.72)
_SHADOW = Vec4(0.0, 0.0, 0.0, 0.8)


class FrameStats:
    """Estadísticas de los frames del último segundo."""

    def __init__(self, window_seconds: float = 1.0) -> None:
        if window_seconds <= 0.0:
            raise ValueError("window_seconds must be positive")
        self._window = window_seconds
        self._samples: deque[float] = deque()
        self._total = 0.0

    @property
    def samples(self) -> int:
        return len(self._samples)

    def add(self, dt: float) -> None:
        # Ignorar pausas, carga inicial y dt inválidos.
        if dt <= 0.0 or dt > 0.5:
            return
        self._samples.append(dt)
        self._total += dt
        while len(self._samples) > 2 and self._total - self._samples[0] >= self._window:
            self._total -= self._samples.popleft()

    def reset(self) -> None:
        self._samples.clear()
        self._total = 0.0

    def fps(self) -> float:
        return self.samples / self._total if self._total > 0.0 else 0.0

    def mean_ms(self) -> float:
        return self._total / self.samples * 1000.0 if self._samples else 0.0

    def worst_ms(self) -> float:
        return max(self._samples) * 1000.0 if self._samples else 0.0


class FpsOverlay:
    """Readout en la esquina inferior derecha de una ``ShowBase``."""

    def __init__(self, base: ShowBase, *, update_interval: float = 0.25) -> None:
        self.base = base
        self.stats = FrameStats()
        self._interval = update_interval
        self._elapsed = 0.0
        self._visible = True
        self._text = OnscreenText(
            text="FPS ...",
            parent=base.aspect2d,
            pos=(0.97, -0.90),
            align=TextNode.ARight,
            scale=0.04,
            fg=_MUTED,
            bg=_CARD,
            shadow=_SHADOW,
            mayChange=True,
            drawOrder=1000,
        )
        base.accept("f3", self.toggle)
        base.taskMgr.add(self._update, "fps-overlay")

    def toggle(self) -> None:
        self._visible = not self._visible
        if self._visible:
            self.stats.reset()
            self._elapsed = 0.0
            self._text.show()
        else:
            self._text.hide()

    def _update(self, task: Any) -> Any:
        dt = globalClock.getDt()
        self.stats.add(dt)
        if self._visible and self.stats.samples:
            self._elapsed += dt
            if self._elapsed >= self._interval:
                self._elapsed = 0.0
                self._refresh()
        return task.cont

    def _refresh(self) -> None:
        fps = self.stats.fps()
        window = self.base.win
        size = f"{window.getXSize()}x{window.getYSize()}" if window is not None else "offscreen"
        self._text.setText(
            f"FPS {fps:5.1f}  {self.stats.mean_ms():5.2f} ms  "
            f"peor {self.stats.worst_ms():5.2f} ms  {size}"
        )
        self._text.setFg(_color(fps))


def _color(fps: float) -> Vec4:
    if fps >= 55.0:
        return _GOOD
    if fps >= 30.0:
        return _WARN
    return _BAD
