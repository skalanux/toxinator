"""LIGA · Noche launcher for Panda3D."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectFrame import DirectFrame
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import Filename, LineSegs, TextNode, Vec4

from toxinator.api.game import Game
from toxinator.api.input import InputState
from toxinator.core.game_host import GameHost
from toxinator.core.games import GameEntry
from toxinator.input.hub import InputHub
from toxinator.launcher import theme, ui
from toxinator.launcher.qr import qr_texture
from toxinator.launcher.ui import Rect

logger = logging.getLogger(__name__)

HINTS = (
    "FLECHAS / TOUCH MOVER  |  ENTER / A ELEGIR  |  D FICHA  |  S AJUSTES  |  "
    "C CELULAR  |  ESC SALIR"
)


@dataclass
class FocusItem:
    rect: Rect
    focus: DirectFrame
    activate: Any


class ConsoleApp(ShowBase):
    """Launcher scene plus a single in-process game at a time."""

    def __init__(
        self,
        hub: InputHub,
        catalog: list[GameEntry],
        phone_url: str,
        *,
        window_type: str = "onscreen",
        screenshot: Path | None = None,
        screenshot_after: float = 3.0,
        seconds: float | None = None,
    ) -> None:
        super().__init__(windowType=window_type)
        self.hub = hub
        self.catalog = catalog
        self.phone_url = phone_url
        self.screenshot = screenshot
        self.screenshot_after = screenshot_after
        self.started_at = time.monotonic()
        self.exit_at = self.started_at + seconds if seconds is not None else None

        self.font_display, self.font_ui, self.font_mono = theme.load_fonts(self)
        self.setBackgroundColor(theme.NAVY)
        self.ui_root = self.aspect2d.attach_new_node("launcher-ui")
        self.overlay_root = self.aspect2d.attach_new_node("launcher-overlay")
        self.overlay_root.hide()

        self.focus_items: list[FocusItem] = []
        self.focus_index = 0
        self._joy_dir: tuple[int, int] | None = None
        self._joy_hold = 0.0
        self._joy_repeat = 0.0
        self.overlay: str | None = None
        self.state = "launcher"
        self.host: GameHost | None = None
        self.pending: GameEntry | None = None
        self.launch_timer = 0.0
        self._last_a = False
        self._slot_texts: list[tuple[Any, Any, Any, Any]] = []

        self.featured = next(
            (entry for entry in catalog if entry.installed),
            catalog[0] if catalog else None,
        )
        self.ladder = [entry for entry in catalog if entry is not self.featured]

        self._build_background()
        self._build_topbar()
        self._build_featured()
        self._build_ladder()
        self._build_bench()
        self._build_overlays()
        self._refresh_focus()

        self.accept("arrow_up", self._move_focus, [0, 1])
        self.accept("arrow_down", self._move_focus, [0, -1])
        self.accept("arrow_left", self._move_focus, [-1, 0])
        self.accept("arrow_right", self._move_focus, [1, 0])
        self.accept("enter", self._activate)
        self.accept("escape", self._on_escape)
        self.accept("d", self._open_detail)
        self.accept("s", self._open_settings)
        self.accept("c", self._open_phone)
        self.taskMgr.add(self._update, "launcher-update")

    # -- scene --------------------------------------------------------------

    def _build_background(self) -> None:
        grid = LineSegs("grid")
        grid.setColor(theme.NAVY_2)
        grid.setThickness(1.0)
        for index in range(-12, 13):
            x = index * 0.11
            grid.moveTo(x, -1.0, 0.0)
            grid.drawTo(x, 1.0, 0.0)
        for index in range(-9, 10):
            z = index * 0.11
            grid.moveTo(-1.33, z, 0.0)
            grid.drawTo(1.33, z, 0.0)
        grid_node = self.ui_root.attach_new_node(grid.create())
        grid_node.setBin("fixed", 0)
        grid_node.setDepthTest(False)

        watermark = ui.text(
            self.ui_root,
            "LIGA",
            (0.0, 0.02),
            0.58,
            Vec4(theme.BONE.x, theme.BONE.y, theme.BONE.z, 0.045),
            self.font_display,
            align=TextNode.ACenter,
            shadow=False,
            bin_number=1,
        )
        watermark.setDepthTest(False)

    def _build_topbar(self) -> None:
        ui.panel(self.ui_root, Rect(-1.30, 1.30, 0.86, 0.97), theme.BONE)

        crest = DirectFrame(
            parent=self.ui_root,
            frameColor=theme.GOLD,
            frameSize=(-1.25, -1.18, 0.88, 0.95),
            relief=DGG.FLAT,
        )
        crest.setBin("fixed", 20)
        ui.text(
            self.ui_root,
            "L",
            (-1.215, 0.895),
            0.065,
            theme.NAVY,
            self.font_display,
            align=TextNode.ACenter,
        )
        ui.text(
            self.ui_root,
            "LIGA",
            (-1.13, 0.895),
            0.072,
            theme.NAVY,
            self.font_display,
        )
        ui.text(
            self.ui_root,
            "LA LIGA DE LOS JUEGOS",
            (-1.13, 0.872),
            0.024,
            theme.CRIMSON,
            self.font_mono,
        )

        ui.text(
            self.ui_root,
            "TEMPORADA 01",
            (-0.06, 0.925),
            0.026,
            theme.MUTED,
            self.font_mono,
            align=TextNode.ACenter,
        )
        fecha = DirectFrame(
            parent=self.ui_root,
            frameColor=theme.GOLD,
            frameSize=(0.08, 0.27, 0.895, 0.945),
            relief=DGG.FLAT,
        )
        fecha.setBin("fixed", 20)
        ui.text(
            self.ui_root,
            "FECHA 03",
            (0.175, 0.907),
            0.028,
            theme.NAVY,
            self.font_display,
            align=TextNode.ACenter,
        )

        self.players_badge = ui.text(
            self.ui_root,
            "PLANTEL 0/4",
            (0.84, 0.925),
            0.027,
            theme.MUTED,
            self.font_mono,
            align=TextNode.ACenter,
        )
        settings_rect = Rect(1.04, 1.26, 0.885, 0.945)
        settings_button, settings_focus = ui.button(
            self.ui_root,
            "AJUSTES",
            settings_rect,
            theme.NAVY,
            theme.BONE,
            self.font_mono,
            self._open_settings,
            text_scale=0.026,
            base_bin=20,
        )
        settings_button.setBin("fixed", 30)
        self.focus_items.append(
            FocusItem(settings_rect, settings_focus, self._open_settings)
        )

    def _build_featured(self) -> None:
        entry = self.featured
        if entry is None:
            return
        ui.panel(self.ui_root, Rect(-1.30, 0.42, -0.58, 0.80), theme.CRIMSON)

        rank = DirectFrame(
            parent=self.ui_root,
            frameColor=theme.GOLD,
            frameSize=(-1.24, -1.05, 0.665, 0.725),
            relief=DGG.FLAT,
        )
        rank.setBin("fixed", 20)
        ui.text(
            self.ui_root,
            f"RANK {entry.rank}",
            (-1.145, 0.678),
            0.029,
            theme.NAVY,
            self.font_display,
            align=TextNode.ACenter,
        )
        ui.text(
            self.ui_root,
            f"EVENTO {entry.event}",
            (-0.98, 0.678),
            0.026,
            theme.BONE,
            self.font_mono,
        )

        ui.text(
            self.ui_root,
            entry.title.upper(),
            (-1.22, 0.505),
            0.105,
            theme.BONE,
            self.font_display,
        )
        ui.text(
            self.ui_root,
            entry.subtitle,
            (-1.22, 0.435),
            0.030,
            theme.GOLD,
            self.font_mono,
        )
        ui.text(
            self.ui_root,
            ui.wrap(entry.description, 48),
            (-1.22, 0.345),
            0.036,
            theme.BONE,
            self.font_ui,
        )

        stat_x = (-1.22, -0.82, -0.40)
        labels = ("JUGADORES", "FORMATOS", "RÉCORD")
        players = (
            f"{entry.players[0]}"
            if entry.players[0] == entry.players[1]
            else f"{entry.players[0]}–{entry.players[1]}"
        )
        values = (players, str(len(entry.modes)), entry.record)
        for x, label, value in zip(stat_x, labels, values, strict=True):
            ui.text(
                self.ui_root,
                label,
                (x, 0.055),
                0.022,
                Vec4(theme.BONE.x, theme.BONE.y, theme.BONE.z, 0.68),
                self.font_mono,
            )
            ui.text(self.ui_root, value, (x, 0.005), 0.050, theme.BONE, self.font_display)

        event = ui.text(
            self.ui_root,
            entry.event,
            (0.16, 0.30),
            0.34,
            Vec4(theme.BONE.x, theme.BONE.y, theme.BONE.z, 0.10),
            self.font_display,
            align=TextNode.ACenter,
            shadow=False,
            bin_number=14,
        )
        event.setDepthTest(False)
        self._build_pin_icon()

        play_button, play_focus = ui.button(
            self.ui_root,
            "JUGAR",
            Rect(-1.20, -0.78, -0.42, -0.30),
            theme.GOLD,
            theme.NAVY,
            self.font_display,
            self._launch_featured,
            text_scale=0.055,
            base_bin=40,
            focus_color=theme.BONE,
        )
        detail_button, detail_focus = ui.button(
            self.ui_root,
            "FICHA",
            Rect(-0.70, -0.32, -0.42, -0.30),
            theme.CRIMSON_DARK,
            theme.BONE,
            self.font_mono,
            self._open_detail,
            text_scale=0.040,
            base_bin=40,
        )
        self.focus_items.extend(
            [
                FocusItem(Rect(-1.20, -0.78, -0.42, -0.30), play_focus, self._launch_featured),
                FocusItem(Rect(-0.70, -0.32, -0.42, -0.30), detail_focus, self._open_detail),
            ]
        )
        _ = (play_button, detail_button)

    def _build_pin_icon(self) -> None:
        segments = LineSegs("pin-icon")
        segments.setColor(theme.BONE)
        segments.setThickness(3.0)
        points = [
            (0.10, 0.02),
            (0.18, 0.05),
            (0.22, 0.14),
            (0.22, 0.25),
            (0.19, 0.33),
            (0.14, 0.38),
            (0.10, 0.38),
            (0.05, 0.33),
            (0.02, 0.25),
            (0.02, 0.14),
            (0.06, 0.05),
            (0.10, 0.02),
        ]
        segments.moveTo(points[0][0], 0.0, points[0][1])
        for x, z in points[1:]:
            segments.drawTo(x, 0.0, z)
        node = self.ui_root.attach_new_node(segments.create())
        node.setBin("fixed", 15)
        node.setDepthTest(False)

        star = ui.text(
            self.ui_root,
            "*",
            (0.12, 0.47),
            0.10,
            theme.GOLD,
            self.font_display,
            align=TextNode.ACenter,
            bin_number=16,
        )
        star.setDepthTest(False)

    def _build_ladder(self) -> None:
        ui.panel(self.ui_root, Rect(0.50, 1.30, -0.58, 0.80), theme.BONE)
        ui.text(
            self.ui_root,
            "PRÓXIMOS DESAFÍOS",
            (0.58, 0.705),
            0.038,
            theme.NAVY,
            self.font_display,
        )
        count = DirectFrame(
            parent=self.ui_root,
            frameColor=theme.GOLD,
            frameSize=(1.17, 1.25, 0.695, 0.745),
            relief=DGG.FLAT,
        )
        count.setBin("fixed", 20)
        ui.text(
            self.ui_root,
            str(len(self.ladder)),
            (1.21, 0.708),
            0.032,
            theme.NAVY,
            self.font_display,
            align=TextNode.ACenter,
        )

        z_positions = (0.50, 0.30)
        for entry, z1 in zip(self.ladder[:2], z_positions, strict=False):
            row = Rect(0.56, 1.24, z1, z1 + 0.15)
            row_button, row_focus = ui.button(
                self.ui_root,
                "",
                row,
                theme.BONE_2,
                theme.NAVY,
                self.font_ui,
                partial(self._open_coming, entry),
                text_scale=0.03,
                base_bin=30,
            )
            rank = DirectFrame(
                parent=self.ui_root,
                frameColor=theme.GOLD if entry.rank == "A" else theme.BONE,
                frameSize=(0.60, 0.68, z1 + 0.035, z1 + 0.115),
                relief=DGG.FLAT,
            )
            rank.setBin("fixed", 40)
            ui.text(
                self.ui_root,
                entry.rank,
                (0.64, z1 + 0.053),
                0.035,
                theme.NAVY,
                self.font_display,
                align=TextNode.ACenter,
            )
            ui.text(
                self.ui_root,
                entry.title.upper(),
                (0.73, z1 + 0.072),
                0.034,
                theme.NAVY,
                self.font_display,
            )
            ui.text(
                self.ui_root,
                entry.subtitle,
                (0.73, z1 + 0.040),
                0.022,
                theme.MUTED,
                self.font_mono,
            )
            ui.text(
                self.ui_root,
                "PRONTO",
                (1.18, z1 + 0.060),
                0.024,
                theme.MUTED,
                self.font_mono,
                align=TextNode.ARight,
            )
            self.focus_items.append(
                FocusItem(row, row_focus, partial(self._open_coming, entry))
            )
            _ = row_button

        add_rect = Rect(0.56, 1.24, 0.08, 0.22)
        add_button, add_focus = ui.button(
            self.ui_root,
            "+ SUMAR DESAFÍO",
            add_rect,
            theme.BONE_2,
            theme.MUTED,
            self.font_mono,
            self._open_add,
            text_scale=0.028,
            base_bin=30,
        )
        self.focus_items.append(FocusItem(add_rect, add_focus, self._open_add))
        _ = add_button

        ui.text(
            self.ui_root,
            "La liga se juega en casa.",
            (0.58, -0.49),
            0.026,
            theme.MUTED,
            self.font_mono,
        )

    def _build_bench(self) -> None:
        ui.panel(self.ui_root, Rect(-1.30, 1.30, -0.90, -0.64), theme.BONE)
        ui.text(
            self.ui_root,
            "PLANTEL",
            (-1.22, -0.685),
            0.040,
            theme.NAVY,
            self.font_display,
        )
        self.bench_count = ui.text(
            self.ui_root,
            "0/4",
            (-0.95, -0.690),
            0.026,
            theme.CRIMSON,
            self.font_mono,
        )
        phone_rect = Rect(0.92, 1.24, -0.735, -0.665)
        phone_button, phone_focus = ui.button(
            self.ui_root,
            "+ SUMAR CELULAR",
            phone_rect,
            theme.NAVY,
            theme.BONE,
            self.font_mono,
            self._open_phone,
            text_scale=0.026,
            base_bin=30,
        )
        self.focus_items.append(FocusItem(phone_rect, phone_focus, self._open_phone))
        _ = phone_button

        slot_x = (-1.22, -0.60, 0.02, 0.64)
        for index, x in enumerate(slot_x):
            frame = DirectFrame(
                parent=self.ui_root,
                frameColor=theme.BONE_2,
                frameSize=(x, x + 0.54, -0.87, -0.755),
                relief=DGG.FLAT,
            )
            frame.setBin("fixed", 20)
            number = ui.text(
                self.ui_root,
                f"P{index + 1}",
                (x + 0.03, -0.775),
                0.026,
                theme.CRIMSON,
                self.font_mono,
            )
            name = ui.text(
                self.ui_root,
                "LIBRE",
                (x + 0.10, -0.785),
                0.024,
                theme.NAVY,
                self.font_mono,
            )
            status = ui.text(
                self.ui_root,
                "",
                (x + 0.10, -0.825),
                0.021,
                theme.MUTED,
                self.font_mono,
            )
            self._slot_texts.append((frame, number, name, status))

        ui.text(
            self.ui_root,
            HINTS,
            (0.0, -0.965),
            0.024,
            theme.MUTED,
            self.font_mono,
            align=TextNode.ACenter,
        )

    # -- overlays -----------------------------------------------------------

    def _build_overlays(self) -> None:
        self.overlay_dim = DirectFrame(
            parent=self.overlay_root,
            frameColor=Vec4(0.015, 0.025, 0.045, 0.84),
            frameSize=(-1.34, 1.34, -1.0, 1.0),
            relief=DGG.FLAT,
        )
        self.overlay_dim.setBin("fixed", 100)

        self.detail_root, self.detail_title = self._overlay_panel(
            "detail",
            "FICHA DEL DESAFÍO",
            "MALDITO PINO",
            "",
        )
        self.detail_body = ui.text(
            self.detail_root,
            "",
            (-0.68, 0.10),
            0.036,
            theme.MUTED,
            self.font_ui,
            bin_number=160,
        )
        detail_play, _ = ui.button(
            self.detail_root,
            "JUGAR",
            Rect(-0.68, -0.12, -0.60, -0.48),
            theme.GOLD,
            theme.NAVY,
            self.font_display,
            self._launch_featured,
            text_scale=0.048,
            base_bin=150,
        )
        detail_close, _ = ui.button(
            self.detail_root,
            "VOLVER",
            Rect(0.02, 0.66, -0.60, -0.48),
            theme.BONE,
            theme.NAVY,
            self.font_mono,
            self._close_overlay,
            text_scale=0.035,
            base_bin=150,
        )
        _ = (detail_play, detail_close)
        self.detail_root.hide()

        self.coming_root, self.coming_title = self._overlay_panel(
            "coming",
            "PRÓXIMAMENTE",
            "KART DE BARRIO",
            "Este desafío todavía está calentando.",
        )
        ui.button(
            self.coming_root,
            "VOLVER",
            Rect(-0.22, 0.22, -0.46, -0.36),
            theme.BONE,
            theme.NAVY,
            self.font_mono,
            self._close_overlay,
            text_scale=0.032,
            base_bin=150,
        )
        self.coming_root.hide()

        self.phone_root, self.phone_title = self._overlay_panel(
            "phone",
            "SUMAR CELULAR",
            "ESCANEÁ EL QR",
            "",
        )
        self.phone_body = ui.text(
            self.phone_root,
            "Misma Wi-Fi que la consola.\nAceptá el certificado autofirmado una vez.",
            (-0.68, 0.28),
            0.030,
            theme.MUTED,
            self.font_ui,
            bin_number=160,
        )
        self.phone_url_text = ui.text(
            self.phone_root,
            "",
            (-0.68, -0.12),
            0.026,
            theme.CRIMSON,
            self.font_mono,
            bin_number=160,
        )
        self.qr_image = OnscreenImage(
            image=qr_texture(self, self.phone_url),
            parent=self.phone_root,
            pos=(0.40, 0.0, -0.02),
            scale=(0.42, 1.0, 0.42),
        )
        self.qr_image.setBin("fixed", 155)
        ui.button(
            self.phone_root,
            "VOLVER",
            Rect(-0.22, 0.22, -0.62, -0.52),
            theme.BONE,
            theme.NAVY,
            self.font_mono,
            self._close_overlay,
            text_scale=0.032,
            base_bin=150,
        )
        self.phone_root.hide()

        self.settings_root, self.settings_title = self._overlay_panel(
            "settings",
            "AJUSTES",
            "CONSOLA",
            "Idioma: Español.\nInglés: próximamente.",
        )
        ui.button(
            self.settings_root,
            "SALIR DE LA LIGA",
            Rect(-0.62, -0.05, -0.55, -0.45),
            theme.CRIMSON,
            theme.BONE,
            self.font_mono,
            self._open_quit,
            text_scale=0.028,
            base_bin=150,
        )
        ui.button(
            self.settings_root,
            "VOLVER",
            Rect(0.05, 0.62, -0.55, -0.45),
            theme.BONE,
            theme.NAVY,
            self.font_mono,
            self._close_overlay,
            text_scale=0.030,
            base_bin=150,
        )
        self.settings_root.hide()

        self.quit_root, self.quit_title = self._overlay_panel(
            "quit",
            "¿CERRAR LA LIGA?",
            "SE TERMINA LA FECHA",
            "Enter para salir. Esc para volver.",
        )
        ui.button(
            self.quit_root,
            "SALIR",
            Rect(-0.62, -0.08, -0.55, -0.45),
            theme.CRIMSON,
            theme.BONE,
            self.font_display,
            self._quit,
            text_scale=0.042,
            base_bin=150,
        )
        ui.button(
            self.quit_root,
            "VOLVER",
            Rect(0.08, 0.62, -0.55, -0.45),
            theme.BONE,
            theme.NAVY,
            self.font_mono,
            self._close_overlay,
            text_scale=0.032,
            base_bin=150,
        )
        self.quit_root.hide()

        self.launch_root = DirectFrame(
            parent=self.overlay_root,
            frameColor=theme.CRIMSON,
            frameSize=(-1.34, 1.34, -1.0, 1.0),
            relief=DGG.FLAT,
        )
        self.launch_root.setBin("fixed", 200)
        ui.text(
            self.launch_root,
            "ENTRANDO A LA CANCHA",
            (0.0, 0.18),
            0.085,
            theme.BONE,
            self.font_display,
            align=TextNode.ACenter,
            bin_number=210,
        )
        self.launch_text = ui.text(
            self.launch_root,
            "",
            (0.0, -0.02),
            0.046,
            theme.GOLD,
            self.font_mono,
            align=TextNode.ACenter,
            bin_number=210,
        )
        ui.text(
            self.launch_root,
            "LA LIGA DE LOS JUEGOS",
            (0.0, -0.82),
            0.026,
            Vec4(theme.BONE.x, theme.BONE.y, theme.BONE.z, 0.65),
            self.font_mono,
            align=TextNode.ACenter,
            bin_number=210,
        )
        self.launch_root.hide()

    def _overlay_panel(
        self,
        overlay: str,
        kicker: str,
        title: str,
        body: str,
    ) -> tuple[DirectFrame, Any]:
        root = self.overlay_root.attach_new_node(f"overlay-{overlay}")
        ui.panel(root, Rect(-0.78, 0.78, -0.70, 0.70), theme.BONE, base_bin=110)
        ui.text(
            root,
            kicker,
            (-0.68, 0.57),
            0.026,
            theme.CRIMSON,
            self.font_mono,
            bin_number=160,
        )
        title_label = ui.text(
            root,
            title.upper(),
            (-0.68, 0.45),
            0.075,
            theme.NAVY,
            self.font_display,
            bin_number=160,
        )
        ui.text(
            root,
            ui.wrap(body, 54),
            (-0.68, 0.32),
            0.034,
            theme.MUTED,
            self.font_ui,
            bin_number=160,
        )
        return root, title_label

    # -- focus / navigation -------------------------------------------------

    def _move_focus(self, dx: int, dy: int) -> None:
        if self.overlay is not None or self.state != "launcher" or not self.focus_items:
            return
        current = self.focus_items[self.focus_index]
        current_x = (current.rect.x1 + current.rect.x2) / 2.0
        current_z = (current.rect.z1 + current.rect.z2) / 2.0
        best_index = -1
        best_score = 1e9
        for index, item in enumerate(self.focus_items):
            if index == self.focus_index:
                continue
            item_x = (item.rect.x1 + item.rect.x2) / 2.0
            item_z = (item.rect.z1 + item.rect.z2) / 2.0
            vx = item_x - current_x
            vz = item_z - current_z
            if dx:
                if vx * dx <= 0.01:
                    continue
                primary, secondary = abs(vx), abs(vz)
            else:
                if vz * dy <= 0.01:
                    continue
                primary, secondary = abs(vz), abs(vx)
            score = primary + secondary * 2.5
            if score < best_score:
                best_score = score
                best_index = index
        if best_index >= 0:
            self.focus_index = best_index
            self._refresh_focus()

    def _refresh_focus(self) -> None:
        for index, item in enumerate(self.focus_items):
            if index == self.focus_index:
                item.focus.show()
            else:
                item.focus.hide()

    def _set_focus_for_rect(self, rect: Rect) -> None:
        for index, item in enumerate(self.focus_items):
            if item.rect == rect:
                self.focus_index = index
                self._refresh_focus()
                return

    # -- actions ------------------------------------------------------------

    def _activate(self) -> None:
        if self.state == "game":
            return
        if self.overlay == "launching":
            return
        if self.overlay == "detail":
            if self.featured is not None and self.featured.installed:
                self._launch_featured()
            else:
                self._close_overlay()
            return
        if self.overlay == "quit":
            self._quit()
            return
        if self.overlay is not None:
            self._close_overlay()
            return
        if self.focus_items:
            self.focus_items[self.focus_index].activate()

    def _on_escape(self) -> None:
        if self.state == "game":
            self._return_to_launcher()
            return
        if self.overlay == "launching":
            self._cancel_launch()
            return
        if self.overlay is not None:
            self._close_overlay()
            return
        self._open_quit()

    def _launch_featured(self) -> None:
        if self.featured is None:
            return
        self._start_launch(self.featured)

    def _start_launch(self, entry: GameEntry) -> None:
        if not entry.installed:
            self._open_coming(entry)
            return
        self.pending = entry
        self.launch_timer = 0.8
        self.overlay = "launching"
        self.overlay_root.show()
        self.overlay_dim.show()
        self.launch_text.setText(entry.title.upper())
        self.launch_root.show()
        self.detail_root.hide()
        self.coming_root.hide()
        self.phone_root.hide()
        self.settings_root.hide()
        self.quit_root.hide()

    def _cancel_launch(self) -> None:
        self.pending = None
        self.overlay = None
        self.launch_root.hide()
        self.overlay_root.hide()
        self.overlay_dim.show()

    def _start_game(self, entry: GameEntry) -> None:
        try:
            game: Game = entry.instantiate()
        except Exception as error:
            logger.exception("no pude cargar %s", entry.id)
            self.launch_text.setText(f"ERROR: {error}")
            self.launch_timer = 2.0
            return
        try:
            self.host = GameHost(self, game, self.hub)
            self.host.start()
        except Exception as error:
            logger.exception("no pude iniciar %s", entry.id)
            if self.host is not None:
                self.host.stop()
                self.host = None
            self.launch_text.setText(f"ERROR: {error}")
            self.launch_timer = 2.0
            return
        self.state = "game"
        self.overlay = None
        self.pending = None
        self.ui_root.hide()
        self.overlay_root.hide()
        self.launch_root.hide()
        self.overlay_dim.show()

    def _return_to_launcher(self) -> None:
        if self.host is not None:
            self.host.stop()
            self.host = None
        self.state = "launcher"
        self.overlay = None
        self.ui_root.show()
        self.overlay_root.hide()
        self.launch_root.hide()
        self.overlay_dim.show()
        self.setBackgroundColor(theme.NAVY)
        self._refresh_focus()

    def _open_detail(self) -> None:
        if self.state != "launcher" or self.featured is None:
            return
        self.overlay = "detail"
        self.overlay_root.show()
        self.overlay_dim.show()
        self.detail_root.show()
        self.coming_root.hide()
        self.phone_root.hide()
        self.settings_root.hide()
        self.quit_root.hide()
        self.launch_root.hide()
        entry = self.featured
        self.detail_body.setText(
            f"{ui.wrap(entry.description, 52)}\n\n"
            f"JUGADORES  {entry.players[0]}\n"
            f"FORMATOS   {', '.join(entry.modes)}\n"
            f"RANK       {entry.rank}\n"
            f"RÉCORD     {entry.record}"
        )

    def _open_coming(self, entry: GameEntry) -> None:
        if self.state != "launcher":
            return
        self.overlay = "coming"
        self.overlay_root.show()
        self.overlay_dim.show()
        self.coming_root.show()
        self.detail_root.hide()
        self.phone_root.hide()
        self.settings_root.hide()
        self.quit_root.hide()
        self.launch_root.hide()
        self.coming_title.setText(entry.title.upper())

    def _open_add(self) -> None:
        self._open_coming(
            GameEntry(
                id="add",
                title="Sumar desafío",
                subtitle="",
                description="",
                rank="—",
                event="—",
                record="—",
                players=(1, 1),
                modes=(),
                installed=False,
                accent="gold",
            )
        )

    def _open_phone(self) -> None:
        if self.state != "launcher":
            return
        self.overlay = "phone"
        self.overlay_root.show()
        self.overlay_dim.show()
        self.phone_root.show()
        self.detail_root.hide()
        self.coming_root.hide()
        self.settings_root.hide()
        self.quit_root.hide()
        self.launch_root.hide()
        self.phone_url_text.setText(ui.wrap(self.phone_url, 30))

    def _open_settings(self) -> None:
        if self.state != "launcher":
            return
        self.overlay = "settings"
        self.overlay_root.show()
        self.overlay_dim.show()
        self.settings_root.show()
        self.detail_root.hide()
        self.coming_root.hide()
        self.phone_root.hide()
        self.quit_root.hide()
        self.launch_root.hide()

    def _open_quit(self) -> None:
        if self.state != "launcher":
            return
        self.overlay = "quit"
        self.overlay_root.show()
        self.overlay_dim.show()
        self.quit_root.show()
        self.detail_root.hide()
        self.coming_root.hide()
        self.phone_root.hide()
        self.settings_root.hide()
        self.launch_root.hide()

    def _close_overlay(self) -> None:
        self.overlay = None
        self.overlay_root.hide()
        self.overlay_dim.show()
        for root in (
            self.detail_root,
            self.coming_root,
            self.phone_root,
            self.settings_root,
            self.quit_root,
            self.launch_root,
        ):
            root.hide()
        self._refresh_focus()

    def _quit(self) -> None:
        self._exit()

    # -- frame --------------------------------------------------------------

    def _update(self, task: Any) -> Any:
        dt = min(max(globalClock.getDt(), 0.0), 0.1)
        now = time.monotonic()

        if self.state == "game":
            if self.host is not None:
                self.host.update(dt)
        else:
            state = self.hub.poll()
            self._update_bench(state)
            frame = state.frame(0)
            if frame is None and state.frames:
                frame = next(iter(state.frames.values()))
            self._update_joystick(frame, dt)
            a_pressed = any(item.button("A") for item in state.frames.values())
            if a_pressed and not self._last_a:
                self._activate()
            self._last_a = a_pressed

        if self.overlay == "launching":
            self.launch_timer -= dt
            if self.launch_timer <= 0.0 and self.pending is not None:
                self._start_game(self.pending)

        if self.screenshot is not None and now - self.started_at >= self.screenshot_after:
            if self.win is not None:
                self.win.saveScreenshot(Filename.from_os_specific(str(self.screenshot)))
                print(f"screenshot: {self.screenshot}", flush=True)
            self._exit()
        elif self.exit_at is not None and now >= self.exit_at:
            self._exit()
        return task.cont

    def _update_joystick(self, frame: Any, dt: float) -> None:
        if self.overlay is not None or self.state != "launcher" or frame is None:
            self._joy_dir = None
            self._joy_hold = 0.0
            self._joy_repeat = 0.0
            return
        if not frame.touch:
            self._joy_dir = None
            self._joy_hold = 0.0
            self._joy_repeat = 0.0
            return
        touch = frame.touch[0]
        dx = touch.x - 0.5
        dy = 0.5 - touch.y
        if max(abs(dx), abs(dy)) < 0.28:
            self._joy_dir = None
            self._joy_hold = 0.0
            self._joy_repeat = 0.0
            return
        horizontal = abs(dx) >= abs(dy)
        direction = (
            (1 if dx > 0 else -1, 0)
            if horizontal
            else (0, 1 if dy > 0 else -1)
        )
        if direction != self._joy_dir:
            self._joy_dir = direction
            self._joy_hold = 0.0
            self._joy_repeat = 0.0
            self._move_focus(*direction)
            return
        self._joy_hold += dt
        if self._joy_hold >= 0.35:
            self._joy_repeat += dt
            if self._joy_repeat >= 0.16:
                self._joy_repeat = 0.0
                self._move_focus(*direction)

    def _update_bench(self, state: InputState) -> None:
        connected = 0
        for slot, (_frame, _number, name, status) in enumerate(self._slot_texts):
            info = state.controller(slot)
            live = state.frame(slot)
            if live is not None:
                connected += 1
                display = info.display_name if info is not None else f"Celular P{slot + 1}"
                name.setText(display.upper())
                status.setText("LISTO")
                status.setFg(theme.JADE)
            elif info is not None:
                name.setText(info.display_name.upper() if info.display_name else f"P{slot + 1}")
                status.setText("GRACIA")
                status.setFg(theme.GOLD)
            else:
                name.setText("LIBRE")
                status.setText("")
                status.setFg(theme.MUTED)
        self.players_badge.setText(f"PLANTEL {connected}/4")
        self.bench_count.setText(f"{connected}/4")

    def _exit(self) -> None:
        if self.host is not None:
            self.host.stop()
            self.host = None
        self.userExit()
