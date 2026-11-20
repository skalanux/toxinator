"""Maldito Pino: first playable bowling slice."""

from __future__ import annotations

import math
from typing import Any

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    NodePath,
    TextNode,
    Vec4,
)

from maldito_pino.lane import DT, HEAD_PIN_Y, POCKET_X, Lane
from maldito_pino.scoring import BowlingMatch
from toxinator.api.game import GameContext, GameManifest
from toxinator.api.input import ControllerFrame

CREAM = Vec4(0.95, 0.92, 0.84, 1.0)
GOLD = Vec4(0.89, 0.70, 0.25, 1.0)
CRIMSON = Vec4(0.69, 0.18, 0.26, 1.0)
MUTED = Vec4(0.62, 0.67, 0.76, 1.0)
JADE = Vec4(0.24, 0.56, 0.49, 1.0)
SKIN = Vec4(0.78, 0.58, 0.45, 1.0)


class MalditoPinoGame:
    """One player, ten frames, phone controller."""

    def __init__(self, manifest: GameManifest) -> None:
        self.manifest = manifest
        self.ctx: GameContext | None = None
        self.base: Any = None
        self.lane: Lane | None = None
        self.match = BowlingMatch()
        self.state = "aim"
        self.standing: set[int] = set(range(10))
        self.aim_x = POCKET_X
        self.charge = 0.0
        self.accumulator = 0.0
        self.roll_elapsed = 0.0
        self.settle_elapsed = 0.0
        self.message = ""
        self.message_timer = 0.0
        self.last_spin = 0.0
        self._frame: ControllerFrame | None = None
        self._hud: dict[str, OnscreenText] = {}
        self.hand: NodePath | None = None
        self.hand_screen: NodePath | None = None
        self.hand_beta = 0.0
        self.hand_gamma = 0.0
        self.swing_time: float | None = None
        self.swing_origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.camera_switched = False
        self.tilt_frame: OnscreenText | None = None
        self.tilt_dot: OnscreenText | None = None

    # -- lifecycle ----------------------------------------------------------

    def start(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self.base = ctx.base
        self.match = BowlingMatch()
        self.standing = set(range(10))
        self.state = "aim"
        self.charge = 0.0
        self.accumulator = 0.0
        self.roll_elapsed = 0.0
        self.settle_elapsed = 0.0
        self.message = ""
        self.message_timer = 0.0

        self._build_lights()
        self.lane = Lane(self.base, ctx.scene)
        self._build_hand()
        self.lane.reset(self.standing)
        self.lane.show_aim(self.aim_x)
        self._build_hud()
        self._set_camera_aim()
        self._show_hand()
        self._update_hud(None)

    def stop(self) -> None:
        if self.hand is not None:
            self.hand.remove_node()
            self.hand = None
        if self.lane is not None:
            self.lane.destroy()
            self.lane = None

    # -- frame --------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.ctx is None or self.lane is None:
            return
        self.message_timer = max(0.0, self.message_timer - dt)
        if self.message_timer == 0.0:
            self.message = ""

        self._update_hand_swing(dt)

        state = self.ctx.input_state
        frame = state.primary_frame()
        self._frame = frame
        self._smooth_hand(frame, dt)

        if self.match.game_over:
            if frame is not None and frame.button("cross"):
                self._restart()
            self._update_hud(frame)
            return

        if self.state == "aim":
            self._update_aim(frame)
        elif self.state == "charge":
            self._update_charge(dt, frame)
        elif self.state == "rolling":
            self._update_rolling(dt, frame)
        elif self.state == "settle":
            self._update_settle(dt, frame)

        self._update_hud(frame)

    # -- states -------------------------------------------------------------

    def _update_aim(self, frame: ControllerFrame | None) -> None:
        assert self.lane is not None
        if frame is None:
            self._pose_hand(charging=False)
            return
        self.last_spin = self._spin_from()
        self._pose_hand(charging=False)
        self.lane.hide_power()
        if frame.pointer is not None:
            self.aim_x = max(-0.45, min(0.45, -0.2 + 0.55 * frame.pointer[0]))
            self.lane.show_aim(self.aim_x)
        if frame.button("cross"):
            self.state = "charge"
            self.charge = 0.0
            self.message = ""
            self.message_timer = 0.0

    def _update_charge(self, dt: float, frame: ControllerFrame | None) -> None:
        self.charge = min(1.0, self.charge + dt * 0.85)
        if frame is None:
            return
        self.last_spin = self._spin_from()
        self._pose_hand(charging=True)
        assert self.lane is not None
        self.lane.show_power(self._power_level())
        if not frame.button("cross"):
            self._throw(frame)

    def _spin_from(self) -> float:
        return max(-1.0, min(1.0, self.hand_gamma / 30.0)) * 12.0

    def _power_level(self) -> float:
        beta_power = max(-1.0, min(1.0, self.hand_beta / 45.0))
        return max(0.0, min(1.0, 0.70 * self.charge + 0.30 * (0.5 + 0.5 * beta_power)))

    def _throw(self, frame: ControllerFrame) -> None:
        assert self.lane is not None
        spin = self._spin_from()
        speed = 5.5 + 4.5 * self._power_level()
        self.last_spin = spin
        self._start_swing()
        self.lane.throw(speed, self.aim_x, spin)
        self.lane.hide_aim()
        self.lane.hide_power()
        self.state = "rolling"
        self.accumulator = 0.0
        self.roll_elapsed = 0.0
        self.camera_switched = False

    def _update_rolling(self, dt: float, frame: ControllerFrame | None) -> None:
        assert self.lane is not None
        self.roll_elapsed += dt
        self.accumulator += min(dt, 0.1)
        while self.accumulator >= DT:
            self.lane.step()
            self.accumulator -= DT
        if not self.camera_switched and self.roll_elapsed >= 0.55:
            self._set_camera_roll()
            self.camera_switched = True
        if self.roll_elapsed > 7.0 or (
            self.roll_elapsed > 0.8 and self.lane.ball_finished()
        ):
            self.state = "settle"
            self.settle_elapsed = 0.0

    def _update_settle(self, dt: float, frame: ControllerFrame | None) -> None:
        assert self.lane is not None
        self.settle_elapsed += dt
        self.accumulator += min(dt, 0.1)
        while self.accumulator >= DT:
            self.lane.step()
            self.accumulator -= DT
        if self.settle_elapsed >= 1.2:
            self._finish_roll()

    def _finish_roll(self) -> None:
        assert self.lane is not None
        remaining = self.lane.remaining()
        fallen = self.standing - remaining
        result = self.match.roll(len(fallen))
        self.standing = remaining

        if result.strike:
            self.message = "PLENO"
        elif result.spare:
            self.message = "SPARE"
        elif len(fallen) == 0:
            self.message = "GUTTER"
        else:
            self.message = f"{len(fallen)} PINOS"
        self.message_timer = 2.0

        if result.game_over:
            self.state = "game_over"
            self.standing = set()
            self._set_camera_aim()
            self._show_hand()
            return

        if self.match.standing == 10:
            self.standing = set(range(10))
        self.state = "aim"
        self.charge = 0.0
        self.lane.reset(self.standing)
        self.lane.show_aim(self.aim_x)
        self._set_camera_aim()
        self._show_hand()

    def _restart(self) -> None:
        assert self.lane is not None
        self.match = BowlingMatch()
        self.standing = set(range(10))
        self.state = "aim"
        self.charge = 0.0
        self.accumulator = 0.0
        self.message = ""
        self.message_timer = 0.0
        self.lane.reset(self.standing)
        self.lane.show_aim(self.aim_x)
        self._set_camera_aim()
        self._show_hand()

    # -- scene --------------------------------------------------------------

    def _box(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
        color: Vec4,
    ) -> NodePath:
        model = self.base.loader.loadModel("models/box")
        model.set_texture_off(1)
        model.set_scale(*size)
        model.set_pos(
            center[0] - size[0] / 2.0,
            center[1] - size[1] / 2.0,
            center[2] - size[2] / 2.0,
        )
        model.set_color(color)
        model.reparent_to(parent)
        return model

    def _build_hand(self) -> None:
        assert self.ctx is not None
        self.hand = self.ctx.scene.attach_new_node("phone-hand")
        # The pivot is the wrist/fist; the phone sits above it. Rotating around
        # the wrist keeps positive and negative tilt visually symmetric.
        self._box(
            self.hand, (0.0, 0.0, 0.17), (0.14, 0.03, 0.24), Vec4(0.93, 0.90, 0.82, 1.0)
        )
        self.hand_screen = self._box(
            self.hand, (0.0, -0.019, 0.17), (0.11, 0.004, 0.18), JADE
        )
        self._box(self.hand, (0.0, -0.022, 0.07), (0.016, 0.004, 0.016), GOLD)

        fist = self.base.loader.loadModel("models/misc/sphere")
        fist.set_texture_off(1)
        fist.set_scale(0.09)
        fist.set_color(SKIN)
        fist.set_pos(0.0, 0.02, 0.0)
        fist.reparent_to(self.hand)

        self._box(
            self.hand, (0.0, 0.03, -0.10), (0.11, 0.11, 0.09), Vec4(0.05, 0.06, 0.09, 1.0)
        )

    def _hand_x(self) -> float:
        return 0.15 + (self.aim_x - 0.15) * 0.5

    def _smooth_hand(self, frame: ControllerFrame | None, dt: float) -> None:
        target_beta = frame.orientation[1] if frame is not None else 0.0
        target_gamma = frame.orientation[2] if frame is not None else 0.0
        if abs(target_beta) < 2.5:
            target_beta = 0.0
        if abs(target_gamma) < 2.5:
            target_gamma = 0.0
        alpha = 1.0 - math.exp(-max(0.0, dt) / 0.22)
        self.hand_beta += (target_beta - self.hand_beta) * alpha
        self.hand_gamma += (target_gamma - self.hand_gamma) * alpha
        if abs(self.hand_beta) < 0.4:
            self.hand_beta = 0.0
        if abs(self.hand_gamma) < 0.4:
            self.hand_gamma = 0.0

    def _pose_hand(self, *, charging: bool) -> None:
        if self.hand is None:
            return
        self.hand.show()
        pitch = max(-85.0, min(85.0, self.hand_beta * 0.95))
        lift = max(-0.06, min(0.06, self.hand_beta * 0.001))
        if charging:
            self.hand.set_pos(
                self._hand_x(),
                -0.45 - 0.10 * self.charge,
                0.68 + lift + 0.04 * self.charge,
            )
            pitch = max(-88.0, min(88.0, pitch - 8.0 * self.charge))
        else:
            self.hand.set_pos(self._hand_x(), -0.35, 0.68 + lift)
        self.hand.set_hpr(0.0, pitch, 0.0)
        if self.hand_screen is not None:
            self.hand_screen.set_color(GOLD if charging else JADE)

    def _show_hand(self) -> None:
        if self.hand is None:
            return
        self.hand.show()
        self._pose_hand(charging=False)

    def _start_swing(self) -> None:
        if self.hand is None:
            return
        self.swing_origin = (
            self._hand_x(),
            -0.45 - 0.10 * self.charge,
            0.68 + max(-0.06, min(0.06, self.hand_beta * 0.001)) + 0.04 * self.charge,
        )
        self.swing_time = 0.0
        self.hand.set_pos(*self.swing_origin)
        if self.hand_screen is not None:
            self.hand_screen.set_color(CRIMSON)

    def _update_hand_swing(self, dt: float) -> None:
        if self.swing_time is None or self.hand is None:
            return
        self.swing_time += dt
        progress = min(1.0, self.swing_time / 0.30)
        origin_x, origin_y, origin_z = self.swing_origin
        self.hand.set_pos(
            origin_x,
            origin_y + 0.65 * progress,
            origin_z + 0.10 * math.sin(math.pi * progress),
        )
        self.hand.set_hpr(0.0, -20.0 * progress, 0.0)
        if progress >= 1.0:
            self.hand.hide()
            self.swing_time = None

    def _build_lights(self) -> None:
        assert self.ctx is not None
        ambient = AmbientLight("ambient")
        ambient.set_color(Vec4(0.62, 0.62, 0.66, 1.0))
        self.ctx.scene.set_light(self.ctx.scene.attach_new_node(ambient))

        key = DirectionalLight("key")
        key.set_color(Vec4(1.0, 0.94, 0.82, 1.0))
        key_node = self.ctx.scene.attach_new_node(key)
        key_node.set_hpr(30.0, -55.0, 0.0)
        self.ctx.scene.set_light(key_node)

    def _set_camera_aim(self) -> None:
        self.base.cam.set_pos(0.0, -6.5, 3.2)
        self.base.cam.look_at(0.0, 9.0, 0.0)
        self.base.camLens.set_fov(55.0)

    def _set_camera_roll(self) -> None:
        self.base.cam.set_pos(0.9, 4.0, 1.2)
        self.base.cam.look_at(0.0, HEAD_PIN_Y, 0.2)
        self.base.camLens.set_fov(55.0)

    # -- HUD ----------------------------------------------------------------

    def _text(
        self,
        name: str,
        *,
        pos: tuple[float, float],
        scale: float,
        color: Vec4,
        align: int = TextNode.ACenter,
    ) -> OnscreenText:
        assert self.ctx is not None
        text = OnscreenText(
            text="",
            parent=self.ctx.ui,
            pos=pos,
            align=align,
            scale=scale,
            fg=color,
            shadow=Vec4(0.0, 0.0, 0.0, 0.7),
            mayChange=True,
        )
        self._hud[name] = text
        return text

    def _build_hud(self) -> None:
        self._text("title", pos=(0.0, 0.93), scale=0.06, color=GOLD)
        self._text("score", pos=(0.0, 0.86), scale=0.045, color=CREAM)
        self._text("frames", pos=(0.0, 0.79), scale=0.030, color=MUTED)
        self._text("message", pos=(0.0, 0.10), scale=0.11, color=GOLD)
        self._text("prompt", pos=(0.0, 0.70), scale=0.040, color=CREAM)
        self._text("power", pos=(-1.32, -0.90), scale=0.050, color=GOLD, align=TextNode.ALeft)
        self._hud["title"].setText("MALDITO PINO")
        self._hud["score"].setText("")

        assert self.ctx is not None
        self.tilt_frame = OnscreenText(
            text="+-------+\n|       |\n|       |\n+-------+",
            parent=self.ctx.ui,
            pos=(1.10, -0.76),
            scale=0.036,
            fg=MUTED,
            align=TextNode.ACenter,
        )
        self.tilt_dot = OnscreenText(
            text="*",
            parent=self.ctx.ui,
            pos=(1.10, -0.81),
            scale=0.060,
            fg=GOLD,
            shadow=Vec4(0.0, 0.0, 0.0, 0.8),
            mayChange=True,
            align=TextNode.ACenter,
        )
        self.tilt_dot.setBin("fixed", 60)
        self.tilt_dot.setDepthTest(False)
        self._text("tilt_label", pos=(1.10, -0.64), scale=0.030, color=MUTED)
        self._hud["tilt_label"].setText("MANO")

    def _update_hud(self, frame: ControllerFrame | None) -> None:
        if not self._hud:
            return
        match = self.match
        total = match.total
        if match.game_over:
            self._hud["score"].setText(f"P1  {total}  |  JUEGO TERMINADO")
        else:
            self._hud["score"].setText(
                f"P1  {total}  |  Turno {match.current_frame}/10  |  "
                f"Bola {match.current_ball}"
            )

        marks = match.frame_marks()
        scores = match.frame_scores()
        parts: list[str] = []
        for index in range(10):
            mark = marks[index] or "."
            value = "" if scores[index] is None else str(scores[index])
            parts.append(f"{index + 1}:{mark}{value}")
        self._hud["frames"].setText("  ".join(parts[:5]) + "\n" + "  ".join(parts[5:]))

        self._hud["message"].setText(self.message)
        self._hud["message"].setFg(GOLD if self.message != "GUTTER" else CRIMSON)

        if frame is None:
            self._hud["prompt"].setText("Conectá el celular desde el QR")
            self._hud["power"].setText("")
            if self.tilt_dot is not None:
                self.tilt_dot.setPos(1.10, -0.84)
            return

        if self.tilt_dot is not None:
            beta = max(-60.0, min(60.0, self.hand_beta))
            self.tilt_dot.setPos(1.10, -0.84 + beta / 60.0 * 0.065)

        if match.game_over:
            self._hud["prompt"].setText("X para otra partida")
            self._hud["power"].setText("")
        elif self.state == "aim":
            self._hud["prompt"].setText(
                "Tocá para apuntar | incliná para efecto | mantené A"
            )
            self._hud["power"].setText(
                f"OBJETIVO {self.aim_x:+.2f} m  |  EFECTO {self.last_spin:+.0f}"
            )
        elif self.state == "charge":
            filled = int(self._power_level() * 10)
            bar = "#" * filled + "-" * (10 - filled)
            self._hud["prompt"].setText("Soltá X para tirar")
            self._hud["power"].setText(f"POTENCIA [{bar}]")
        elif self.state == "rolling":
            self._hud["prompt"].setText("Rodando...")
            self._hud["power"].setText("")
        else:
            self._hud["prompt"].setText("...")
            self._hud["power"].setText("")

        if self.state == "aim" and self.message:
            self._hud["message"].setText(self.message)
