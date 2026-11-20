"""Minimal game host for the first playable slice."""

from __future__ import annotations

import logging
import time
from typing import Any

from toxinator.api.game import API_VERSION, Game, GameContext
from toxinator.api.input import InputState
from toxinator.api.phone import NullPhoneService, PhoneService
from toxinator.input.hub import InputHub

logger = logging.getLogger(__name__)


class GameHost:
    """Own the game scene/UI roots and its lifecycle."""

    def __init__(
        self,
        base: Any,
        game: Game,
        input_hub: InputHub,
        *,
        locale: str = "es",
        phone: PhoneService | None = None,
    ) -> None:
        self.base = base
        self.game = game
        self.input = input_hub
        self.scene = base.render.attach_new_node(f"game-{game.manifest.id}")
        self.ui = base.aspect2d.attach_new_node(f"game-ui-{game.manifest.id}")
        self.ctx = GameContext(
            base=base,
            scene=self.scene,
            ui=self.ui,
            input_state=InputState(time.monotonic(), {}, {}),
            locale=locale,
            phone=phone or NullPhoneService(),
            request_exit=base.userExit,
        )
        self.started = False

    def start(self) -> None:
        if self.game.manifest.requires_api != API_VERSION:
            raise RuntimeError(
                f"{self.game.manifest.id} requiere API "
                f"{self.game.manifest.requires_api}, consola {API_VERSION}"
            )
        self.game.start(self.ctx)
        self.started = True

    def update(self, dt: float) -> None:
        self.ctx.input_state = self.input.poll()
        self.game.update(min(max(dt, 0.0), 0.1))

    def stop(self) -> None:
        if self.started:
            try:
                self.game.stop()
            except Exception:
                logger.exception("game stop failed")
            self.started = False
        self.ctx.phone.stop()
        self.scene.remove_node()
        self.ui.remove_node()
