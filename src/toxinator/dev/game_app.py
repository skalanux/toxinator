"""Panda3D app that hosts a game and the phone input hub."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import Filename

from toxinator.api.game import Game
from toxinator.api.phone import PhoneService
from toxinator.core.game_host import GameHost
from toxinator.input.hub import InputHub
from toxinator.input.keyboard import KeyboardMouseSource


class GameApp(ShowBase):
    """Console-owned ShowBase for a single game."""

    def __init__(
        self,
        hub: InputHub,
        game: Game,
        *,
        window_type: str = "onscreen",
        screenshot: Path | None = None,
        screenshot_after: float = 3.0,
        seconds: float | None = None,
        phone: PhoneService | None = None,
        keyboard: KeyboardMouseSource | None = None,
    ) -> None:
        super().__init__(windowType=window_type)
        self.setBackgroundColor(0.025, 0.04, 0.07, 1.0)
        self.screenshot = screenshot
        self.screenshot_after = screenshot_after
        self.started_at = time.monotonic()
        self.exit_at = self.started_at + seconds if seconds is not None else None
        self.keyboard = keyboard
        if keyboard is not None:
            keyboard.attach(self)

        self.host = GameHost(self, game, hub, phone=phone)
        self.host.start()
        self.accept("escape", self._exit)
        self.taskMgr.add(self._update, "game-update")

    def _update(self, task: Any) -> Any:
        self.host.update(globalClock.getDt())

        now = time.monotonic()
        if self.screenshot is not None and now - self.started_at >= self.screenshot_after:
            if self.win is not None:
                self.win.saveScreenshot(Filename.from_os_specific(str(self.screenshot)))
                print(f"screenshot: {self.screenshot}", flush=True)
            self._exit()
        elif self.exit_at is not None and now >= self.exit_at:
            self._exit()
        return task.cont

    def _exit(self) -> None:
        self.host.stop()
        if self.keyboard is not None:
            self.keyboard.detach()
        self.userExit()
