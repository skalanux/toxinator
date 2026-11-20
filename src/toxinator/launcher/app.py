"""TOXINATOR launcher: a widescreen console home with a navigable catalog."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectButton import DirectButton
from direct.gui.DirectFrame import DirectFrame
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import Filename, LineSegs, TextNode, Vec4

from toxinator.api.game import Game
from toxinator.api.input import InputState
from toxinator.api.phone import PhoneService
from toxinator.core.game_host import GameHost
from toxinator.core.games import GameEntry
from toxinator.input.hub import InputHub
from toxinator.input.keyboard import KeyboardMouseSource
from toxinator.launcher import art, theme, ui
from toxinator.launcher.qr import qr_texture
from toxinator.launcher.ui import Rect

logger = logging.getLogger(__name__)

HINTS_HOME = (
    "Flechas o mouse mover   ·   Enter elegir   ·   S ajustes   ·   C celular"
)
HINTS_CATALOG = (
    "Flechas o mouse mover   ·   Enter abrir ficha   ·   Esc volver   ·   S ajustes"
)

MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

SIDEBAR_X1 = -1.78
SIDEBAR_X2 = -1.06
CONTENT_X1 = -0.98
CONTENT_X2 = 1.72
SCREEN = Rect(-1.79, 1.79, -1.01, 1.01)

FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "Todos"),
    ("installed", "Instalados"),
    ("multi", "Para varios"),
    ("upcoming", "Próximamente"),
)
PAGE_SIZE = 8


@dataclass
class FocusItem:
    key: str
    rect: Rect
    ring: Any | None
    activate: Callable[[], None]
    on_focus: Callable[[], None] | None = None
    data: dict[str, Any] = field(default_factory=dict)


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
        set_mode: Callable[[str], None] | None = None,
        set_controller: Callable[[dict[str, Any] | None], None] | None = None,
        set_game_assets: Callable[[str, Path | None], None] | None = None,
        phone: PhoneService | None = None,
        keyboard: KeyboardMouseSource | None = None,
    ) -> None:
        super().__init__(windowType=window_type)
        self.hub = hub
        self.catalog = catalog
        self.phone_url = phone_url
        self.phone_secure = phone_url.startswith("https://")
        self._set_mode_callback = set_mode or (lambda mode: None)
        self._set_controller_callback = set_controller or (lambda profile: None)
        self._set_game_assets_callback = set_game_assets or (lambda _id, _root: None)
        self.phone = phone
        self.keyboard = keyboard
        if keyboard is not None:
            keyboard.attach(self)
            keyboard.state.set_wasd(False)
        self.screenshot = screenshot
        self.screenshot_after = screenshot_after
        self.started_at = time.monotonic()
        self.exit_at = self.started_at + seconds if seconds is not None else None

        (
            self.font_display,
            self.font_ui,
            self.font_bold,
            self.font_mono,
        ) = theme.load_fonts(self)
        self.palette = theme.PALETTE
        self.setBackgroundColor(self.palette.bg)

        self.ui_root: Any = None
        self.overlay_root: Any = None
        self.home_root: Any = None
        self.catalog_root: Any = None
        self.catalog_dynamic_root: Any = None
        self.home_shadow_root: Any = None

        self.screen = "home"
        self.overlay: str | None = None
        self.state = "launcher"
        self.focus_items: list[FocusItem] = []
        self.focus_index = 0
        self._screen_items: dict[str, list[FocusItem]] = {}
        self._overlay_items: dict[str, list[FocusItem]] = {}
        self._screen_focus_key: dict[str, str] = {}
        self._last_focus_key = ""

        self.shelf_entries = self._shelf_entries()
        self.hero_entry: GameEntry | None = self.shelf_entries[0] if self.shelf_entries else None
        self.detail_entry: GameEntry | None = None
        self.catalog_filter = "all"
        self.catalog_page = 0

        self.sidebar_items: list[FocusItem] = []
        self.home_items: list[FocusItem] = []
        self.catalog_items: list[FocusItem] = []
        self.nav_visuals: dict[str, dict[str, Any]] = {}

        self._hero_widgets: dict[str, Any] = {}
        self._catalog_count: Any = None
        self._catalog_tabs_root: Any = None
        self._catalog_grid_root: Any = None
        self._catalog_page_text: Any = None
        self._catalog_page_items: list[FocusItem] = []

        self._controller_rows: list[tuple[Any, Any, Any, Any]] = []
        self._controller_chips: list[tuple[Any, Any, Any]] = []
        self._controller_count_text: Any = None
        self._controller_summary: Any = None
        self._clock_text: Any = None
        self._date_text: Any = None
        self._last_clock = ""

        self.settings_root: Any = None
        self.controllers_root: Any = None
        self.detail_root: Any = None
        self.phone_root: Any = None
        self.quit_root: Any = None
        self.launch_root: Any = None
        self.overlay_dim: Any = None
        self.launch_text: Any = None
        self.detail_widgets: dict[str, Any] = {}
        self.phone_widgets: dict[str, Any] = {}
        self.qr_image: Any = None

        self.host: GameHost | None = None
        self.pending: GameEntry | None = None
        self.launch_timer = 0.0
        self._last_a = False
        self._last_b = False
        self._has_controller = False
        self._pairing_dismissed = False
        self._phone_waiting = False
        self._joy_dir: tuple[int, int] | None = None
        self._joy_hold = 0.0
        self._joy_repeat = 0.0

        self._build_ui()
        self._refresh_clock(datetime.now())
        self._refresh_controllers_empty()

        if keyboard is None:
            self.accept("arrow_up", self._move_focus, [0, 1])
            self.accept("arrow_down", self._move_focus, [0, -1])
            self.accept("arrow_left", self._move_focus, [-1, 0])
            self.accept("arrow_right", self._move_focus, [1, 0])
            self.accept("enter", self._activate)
            self.accept("escape", self._on_escape)
        self.accept("d", self._open_detail_from_focus)
        self.accept("s", self._open_settings)
        self.accept("c", self._open_phone)
        self.taskMgr.add(self._update, "launcher-update")
        # Timers start once the UI is ready, so screenshots and --seconds do not
        # count texture generation.
        self.started_at = time.monotonic()
        self.exit_at = self.started_at + seconds if seconds is not None else None
        self._notify_mode("launcher")

    # -- catalog helpers -----------------------------------------------------

    def _bind_enter(self, node: Any, command: Callable[[], None]) -> None:
        def run(_event: Any) -> None:
            command()

        node.bind(DGG.ENTER, run)

    def _hotspot(
        self,
        parent: Any,
        rect: Rect,
        command: Callable[[], None],
        *,
        bin_number: int = 30,
    ) -> DirectButton:
        button = DirectButton(
            parent=parent,
            text="",
            frameColor=(0.0, 0.0, 0.0, 0.0),
            frameSize=(rect.x1, rect.x2, rect.z1, rect.z2),
            relief=DGG.FLAT,
            command=command,
            pressEffect=0,
            rolloverSound=None,
            clickSound=None,
        )
        button.setBin("fixed", bin_number)
        return button

    def _shelf_entries(self) -> list[GameEntry]:
        installed = [entry for entry in self.catalog if entry.installed]
        upcoming = [entry for entry in self.catalog if not entry.installed]
        return (installed + upcoming)[:5]

    def _entry(self, game_id: str | None) -> GameEntry | None:
        if game_id is None:
            return None
        return next((entry for entry in self.catalog if entry.id == game_id), None)

    def _filter_entries(self, filter_id: str) -> list[GameEntry]:
        if filter_id == "installed":
            return [entry for entry in self.catalog if entry.installed]
        if filter_id == "upcoming":
            return [entry for entry in self.catalog if not entry.installed]
        if filter_id == "multi":
            return [entry for entry in self.catalog if entry.players[1] >= 2]
        return list(self.catalog)

    def _filtered_catalog(self) -> list[GameEntry]:
        return self._filter_entries(self.catalog_filter)

    def _page_count(self) -> int:
        return max(1, (len(self._filtered_catalog()) + PAGE_SIZE - 1) // PAGE_SIZE)

    def _page_entries(self) -> list[GameEntry]:
        entries = self._filtered_catalog()
        self.catalog_page = min(self.catalog_page, self._page_count() - 1)
        start = self.catalog_page * PAGE_SIZE
        return entries[start : start + PAGE_SIZE]

    # -- build ---------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setBackgroundColor(self.palette.bg)
        self.ui_root = self.aspect2d.attach_new_node("launcher-ui")
        self.overlay_root = self.aspect2d.attach_new_node("launcher-overlay")
        self.overlay_root.hide()

        self.sidebar_items = []
        self.home_items = []
        self.catalog_items = []
        self.nav_visuals = {}
        self._overlay_items = {}
        self._hero_widgets = {}
        self._controller_rows = []
        self._controller_chips = []

        self._build_background()
        self._build_sidebar()
        self._build_home()
        self._build_catalog()
        self._build_overlays()
        self._refresh_hero()
        self._refresh_nav()
        self._last_clock = ""
        self._refresh_clock(datetime.now())
        self._show_screen(self.screen, restore=True)

    def _build_background(self) -> None:
        wallpaper = art.wallpaper_texture(self.palette)
        ui.image(self.ui_root, wallpaper, SCREEN, bin_number=0)
        # A soft top edge keeps the rail and the content tied together.
        ui.image(
            self.ui_root,
            art.rounded_texture(8, 8, 0, theme.with_alpha(self.palette.line, 0.35)),
            Rect(-1.79, 1.79, 0.985, 1.01),
            bin_number=1,
        )

    def _build_sidebar(self) -> None:
        selected = self.palette
        ui.rounded(
            self.ui_root,
            Rect(SIDEBAR_X1, SIDEBAR_X2, -1.0, 1.0),
            selected.panel,
            radius=0,
            bin_number=4,
            name="sidebar",
        )
        ui.rounded(
            self.ui_root,
            Rect(SIDEBAR_X2 - 0.004, SIDEBAR_X2, -1.0, 1.0),
            theme.with_alpha(selected.line, 0.9),
            radius=0,
            bin_number=6,
            name="sidebar-rule",
        )

        self._hud_frame(selected)

        self.nav_selected_mark = ui.image(
            self.ui_root,
            art.circle_texture(32, selected.accent),
            Rect(-1.71, -1.605, 0.865, 0.97),
            bin_number=20,
        )
        ui.text(
            self.ui_root,
            "T",
            (-1.6575, 0.901),
            0.036,
            selected.accent_ink,
            self.font_display,
            align=TextNode.ACenter,
            bin_number=66,
        )
        ui.text(
            self.ui_root,
            "TOXINATOR",
            (-1.585, 0.902),
            0.060,
            selected.text,
            self.font_display,
            bin_number=60,
        )
        ui.text(
            self.ui_root,
            "CONSOLA · 3",
            (-1.705, 0.838),
            0.021,
            selected.accent,
            self.font_mono,
            bin_number=60,
        )

        nav_defs = (
            ("home", "Inicio", "home", "Ir al inicio"),
            ("catalog", "Catálogo", "catalog", "Ver todos los juegos"),
            ("controllers", "Mandos", "controller", "Estado de los controles"),
            ("settings", "Ajustes", "settings", "Información y salida"),
        )
        for index, (key, label, icon_name, _hint) in enumerate(nav_defs):
            z2 = 0.700 - index * 0.118
            rect = Rect(-1.72, -1.08, z2 - 0.094, z2)
            background = ui.rounded(
                self.ui_root,
                rect,
                selected.raised,
                radius=12,
                bin_number=11,
                name="nav-active",
            )
            marker = ui.rounded(
                self.ui_root,
                Rect(rect.x1, rect.x1 + 0.014, rect.center[1] - 0.030, rect.center[1] + 0.030),
                selected.accent,
                radius=4,
                bin_number=13,
                name="nav-marker",
            )
            icon_node = ui.icon(
                self.ui_root,
                icon_name,
                (rect.x1 + 0.065, rect.center[1]),
                0.058,
                selected.muted,
                thickness=2.2,
                bin_number=61,
            )
            label_node = ui.text(
                self.ui_root,
                label,
                (rect.x1 + 0.112, rect.center[1] - 0.013),
                0.036,
                selected.muted,
                self.font_bold,
                bin_number=62,
            )
            focus_ring = ui.rounded(
                self.ui_root,
                rect.grow(0.006),
                selected.accent,
                radius=14,
                bin_number=10,
                name="nav-focus",
            )
            focus_ring.hide()
            hotspot = self._hotspot(
                self.ui_root,
                rect,
                partial(self._nav_activate, key),
                bin_number=15,
            )
            self._bind_enter(hotspot, partial(self._set_focus_key, f"nav:{key}"))

            def activate(key: str = key) -> None:
                self._nav_activate(key)

            self.sidebar_items.append(
                FocusItem(
                    key=f"nav:{key}",
                    rect=rect,
                    ring=focus_ring,
                    activate=activate,
                )
            )
            self.nav_visuals[key] = {
                "background": background,
                "marker": marker,
                "icon": icon_node,
                "label": label_node,
            }

        # Clock, date and controller state.
        self._clock_text = ui.text(
            self.ui_root,
            "00:00",
            (-1.705, -0.545),
            0.110,
            selected.text,
            self.font_display,
            bin_number=60,
        )
        self._date_text = ui.text(
            self.ui_root,
            "",
            (-1.705, -0.640),
            0.025,
            selected.muted,
            self.font_mono,
            bin_number=60,
        )
        ui.rounded(
            self.ui_root,
            Rect(-1.70, -1.10, -0.690, -0.689),
            theme.with_alpha(selected.line, 0.9),
            radius=0,
            bin_number=12,
            name="sidebar-divider",
        )
        self._controller_summary = ui.text(
            self.ui_root,
            "MANDOS 0/4",
            (-1.705, -0.760),
            0.024,
            selected.muted,
            self.font_mono,
            bin_number=60,
        )

        for slot in range(4):
            x1 = -1.705 + slot * 0.150
            rect = Rect(x1, x1 + 0.138, -0.865, -0.810)
            ui.rounded(
                self.ui_root,
                rect,
                theme.with_alpha(selected.raised, 0.72),
                radius=9,
                bin_number=12,
                name="controller-chip",
            )
            dot = ui.image(
                self.ui_root,
                art.circle_texture(32, ui.WHITE),
                Rect(x1 + 0.014, x1 + 0.036, -0.8485, -0.8265),
                color=selected.muted,
                bin_number=61,
            )
            label = ui.text(
                self.ui_root,
                f"P{slot + 1}",
                (x1 + 0.045, -0.850),
                0.020,
                selected.muted,
                self.font_mono,
                bin_number=62,
            )
            self._controller_chips.append((dot, label, rect))

        ui.text(
            self.ui_root,
            "C · vincular mando",
            (-1.705, -0.933),
            0.019,
            selected.muted,
            self.font_mono,
            bin_number=60,
        )

    def _build_home(self) -> None:
        selected = self.palette
        self.home_root = self.ui_root.attach_new_node("home-screen")

        hero = Rect(CONTENT_X1, CONTENT_X2, -0.085, 0.850)
        ui.rounded(
            self.home_root,
            hero.grow(0.004),
            selected.line,
            radius=20,
            bin_number=8,
            name="hero-edge",
        )
        hero_texture = (
            art.game_art_texture(
                self.hero_entry.id,
                "hero",
                560,
                236,
                20,
                motif=self.hero_entry.art_motif,
            )
            if self.hero_entry is not None
            else art.rounded_texture(560, 236, 20, selected.raised)
        )
        self._hero_widgets["art"] = ui.image(
            self.home_root, hero_texture, hero, bin_number=9
        )

        text_x = hero.x1 + 0.105
        self._hero_widgets["eyebrow"] = ui.text(
            self.home_root,
            "LISTO PARA JUGAR",
            (text_x, 0.735),
            0.026,
            selected.accent,
            self.font_mono,
            bin_number=60,
        )
        self._hero_widgets["title"] = ui.text(
            self.home_root,
            "TOXINATOR",
            (text_x, 0.600),
            0.120,
            selected.text,
            self.font_display,
            bin_number=60,
        )
        self._hero_widgets["subtitle"] = ui.text(
            self.home_root,
            "",
            (text_x, 0.505),
            0.027,
            selected.muted,
            self.font_mono,
            bin_number=60,
        )
        self._hero_widgets["description"] = ui.text(
            self.home_root,
            "",
            (text_x, 0.410),
            0.034,
            selected.text,
            self.font_ui,
            bin_number=60,
        )

        self._hero_widgets["pills"] = []
        pill_specs = (0.300, 0.255, 0.270)
        pill_x = text_x
        for width in pill_specs:
            rect = Rect(pill_x, pill_x + width, 0.185, 0.245)
            label = ui.pill(
                self.home_root,
                "",
                rect,
                theme.with_alpha(selected.raised, 0.9),
                selected.text,
                self.font_mono,
                text_scale=0.026,
                bin_number=50,
            )
            self._hero_widgets["pills"].append((rect, label))
            pill_x += width + 0.018

        play_rect = Rect(text_x, text_x + 0.270, -0.060, 0.060)
        detail_rect = Rect(text_x + 0.300, text_x + 0.540, -0.060, 0.060)
        play_button, play_ring = ui.button(
            self.home_root,
            "Jugar",
            play_rect,
            selected.accent,
            selected.accent_ink,
            self.font_bold,
            self._launch_hero,
            text_scale=0.034,
            base_bin=40,
            radius=12,
            ring_color=selected.text,
        )
        detail_button, detail_ring = ui.button(
            self.home_root,
            "Ficha",
            detail_rect,
            theme.with_alpha(selected.raised, 0.92),
            selected.text,
            self.font_bold,
            self._open_detail_from_focus,
            text_scale=0.030,
            base_bin=40,
            radius=12,
            ring_color=selected.accent,
        )
        self._hero_widgets["play_label"] = play_button
        self._hero_widgets["detail_label"] = detail_button
        self.home_items.extend(
            [
                FocusItem(
                    key="hero:play",
                    rect=play_rect,
                    ring=play_ring,
                    activate=self._launch_hero,
                ),
                FocusItem(
                    key="hero:detail",
                    rect=detail_rect,
                    ring=detail_ring,
                    activate=self._open_detail_from_focus,
                ),
            ]
        )

        ui.text(
            self.home_root,
            "Tus juegos",
            (CONTENT_X1, -0.205),
            0.038,
            selected.text,
            self.font_display,
            bin_number=60,
        )
        all_rect = Rect(1.49, 1.72, -0.240, -0.168)
        all_button, all_ring = ui.button(
            self.home_root,
            "Ver catálogo",
            all_rect,
            theme.with_alpha(selected.raised, 0.0),
            selected.accent,
            self.font_mono,
            lambda: self._show_screen("catalog"),
            text_scale=0.028,
            base_bin=40,
            radius=9,
            ring_color=selected.accent,
        )
        self.home_items.append(
            FocusItem(
                key="shelf:all",
                rect=all_rect,
                ring=all_ring,
                activate=lambda: self._show_screen("catalog"),
            )
        )
        _ = all_button

        count = len(self.shelf_entries) + 1
        gap = 0.034
        width = min(0.520, (CONTENT_X2 - CONTENT_X1 - gap * (count - 1)) / count)
        card_z1, card_z2 = -0.665, -0.300
        for index, entry in enumerate(self.shelf_entries):
            x1 = CONTENT_X1 + index * (width + gap)
            rect = Rect(x1, x1 + width, card_z1, card_z2)
            self._build_shelf_card(entry, rect)
        cta_x = CONTENT_X1 + len(self.shelf_entries) * (width + gap)
        cta_rect = Rect(cta_x, cta_x + width, card_z1, card_z2)
        self._build_catalog_cta(cta_rect)

        ui.text(
            self.home_root,
            HINTS_HOME,
            (CONTENT_X1, -0.945),
            0.024,
            selected.muted,
            self.font_mono,
            bin_number=60,
        )
        self._screen_items["home"] = self.home_items

    def _build_shelf_card(self, entry: GameEntry, rect: Rect) -> None:
        selected = self.palette
        ring = ui.rounded(
            self.home_root,
            rect.grow(0.007),
            selected.accent,
            radius=18,
            bin_number=19,
            name="shelf-focus",
        )
        ring.hide()
        texture = art.game_art_texture(
            entry.id,
            "card",
            220,
            165,
            16,
            motif=entry.art_motif,
        )
        ui.image(self.home_root, texture, rect, bin_number=20)
        ui.image(
            self.home_root,
            art.circle_texture(24, selected.status if entry.installed else selected.muted),
            Rect(rect.x2 - 0.035, rect.x2 - 0.013, rect.z2 - 0.035, rect.z2 - 0.013),
            bin_number=22,
        )
        ui.text(
            self.home_root,
            entry.title.upper(),
            (rect.x1 + 0.022, rect.z1 + 0.088),
            0.032,
            selected.text,
            self.font_display,
            bin_number=60,
        )
        genre = entry.subtitle or entry.id
        ui.text(
            self.home_root,
            genre.upper(),
            (rect.x1 + 0.022, rect.z1 + 0.052),
            0.021,
            selected.text,
            self.font_mono,
            bin_number=60,
        )

        def focus(entry: GameEntry = entry) -> None:
            self._focus_entry(entry)

        def activate(entry: GameEntry = entry) -> None:
            self._open_detail(entry)

        button = self._hotspot(
            self.home_root,
            rect,
            partial(self._open_detail, entry),
            bin_number=25,
        )
        self._bind_enter(button, partial(self._focus_entry, entry))

        self.home_items.append(
            FocusItem(
                key=f"shelf:{entry.id}",
                rect=rect,
                ring=ring,
                activate=activate,
                on_focus=focus,
            )
        )

    def _build_catalog_cta(self, rect: Rect) -> None:
        selected = self.palette
        ring = ui.rounded(
            self.home_root,
            rect.grow(0.007),
            selected.accent,
            radius=18,
            bin_number=19,
            name="cta-focus",
        )
        ring.hide()
        ui.rounded(
            self.home_root,
            rect,
            theme.with_alpha(selected.raised, 0.92),
            radius=16,
            bin_number=20,
            name="cta",
        )
        ui.icon(
            self.home_root,
            "plus",
            (rect.center[0], rect.center[1] + 0.055),
            0.060,
            selected.accent,
            thickness=2.2,
            bin_number=61,
        )
        ui.text(
            self.home_root,
            "Ver catálogo",
            (rect.x1 + 0.025, rect.z1 + 0.088),
            0.032,
            selected.text,
            self.font_display,
            bin_number=60,
        )
        ui.text(
            self.home_root,
            f"{len(self.catalog)} juegos",
            (rect.x1 + 0.025, rect.z1 + 0.052),
            0.021,
            selected.muted,
            self.font_mono,
            bin_number=60,
        )
        button = self._hotspot(
            self.home_root,
            rect,
            partial(self._show_screen, "catalog"),
            bin_number=25,
        )
        self._bind_enter(button, partial(self._set_focus_key, "shelf:catalog"))
        self.home_items.append(
            FocusItem(
                key="shelf:catalog",
                rect=rect,
                ring=ring,
                activate=lambda: self._show_screen("catalog"),
            )
        )

    def _build_catalog(self) -> None:
        selected = self.palette
        self.catalog_root = self.ui_root.attach_new_node("catalog-screen")
        ui.text(
            self.catalog_root,
            "BIBLIOTECA",
            (CONTENT_X1, 0.855),
            0.024,
            selected.accent,
            self.font_mono,
            bin_number=60,
        )
        ui.text(
            self.catalog_root,
            "Catálogo",
            (CONTENT_X1, 0.735),
            0.100,
            selected.text,
            self.font_display,
            bin_number=60,
        )
        self._catalog_count = ui.text(
            self.catalog_root,
            f"{len(self.catalog)} juegos",
            (CONTENT_X2, 0.760),
            0.026,
            selected.muted,
            self.font_mono,
            align=TextNode.ARight,
            bin_number=60,
        )
        ui.text(
            self.catalog_root,
            "Todo lo que puede jugar la consola, en un solo lugar.",
            (CONTENT_X1, 0.690),
            0.028,
            selected.muted,
            self.font_ui,
            bin_number=60,
        )
        ui.text(
            self.catalog_root,
            HINTS_CATALOG,
            (CONTENT_X1, -0.945),
            0.024,
            selected.muted,
            self.font_mono,
            bin_number=60,
        )
        self._rebuild_catalog_dynamic(focus_key=None)

    def _rebuild_catalog_dynamic(self, *, focus_key: str | None) -> None:
        selected = self.palette
        if self.catalog_dynamic_root is not None:
            self.catalog_dynamic_root.remove_node()
        root = self.catalog_root.attach_new_node("catalog-dynamic")
        self.catalog_dynamic_root = root
        items: list[FocusItem] = []

        tab_x = CONTENT_X1
        for filter_id, label in FILTERS:
            entries = self._filter_entries(filter_id)
            active = filter_id == self.catalog_filter
            width = 0.190 + len(label) * 0.013
            rect = Rect(tab_x, tab_x + width, 0.575, 0.655)
            fill = selected.accent if active else theme.with_alpha(selected.raised, 0.55)
            text_color = selected.accent_ink if active else selected.muted
            ring = ui.rounded(
                root,
                rect.grow(0.005),
                selected.text,
                radius=11,
                bin_number=28,
                name="tab-focus",
            )
            ring.hide()
            ui.rounded(root, rect, fill, radius=9, bin_number=30, name="tab")
            ui.text(
                root,
                f"{label}  {len(entries)}",
                (rect.center[0], rect.center[1] - 0.012),
                0.024,
                text_color,
                self.font_mono,
                align=TextNode.ACenter,
                bin_number=60,
            )
            button = self._hotspot(
                root,
                rect,
                partial(self._pick_filter, filter_id),
                bin_number=32,
            )
            self._bind_enter(button, partial(self._set_focus_key, f"filter:{filter_id}"))
            items.append(
                FocusItem(
                    key=f"filter:{filter_id}",
                    rect=rect,
                    ring=ring,
                    activate=partial(self._pick_filter, filter_id),
                )
            )
            tab_x += width + 0.028

        entries = self._page_entries()
        gap_x = 0.050
        card_width = (CONTENT_X2 - CONTENT_X1 - gap_x * 3) / 4
        art_height = 0.500
        row_pitch = 0.680
        for index, entry in enumerate(entries):
            column = index % 4
            row = index // 4
            x1 = CONTENT_X1 + column * (card_width + gap_x)
            z2 = 0.455 - row * row_pitch
            rect = Rect(x1, x1 + card_width, z2 - art_height, z2)
            self._build_catalog_card(root, entry, rect, items)

        pages = self._page_count()
        self._catalog_page_items = []
        if pages > 1:
            page_text = ui.text(
                root,
                f"Página {self.catalog_page + 1} de {pages}",
                (CONTENT_X1, -0.900),
                0.022,
                selected.muted,
                self.font_mono,
                bin_number=60,
            )
            self._catalog_page_text = page_text
            controls_y = (-0.930, -0.878)
            previous_rect = Rect(1.28, 1.46, controls_y[0], controls_y[1])
            next_rect = Rect(1.49, 1.72, controls_y[0], controls_y[1])
            if self.catalog_page > 0:
                items.append(self._page_button(root, "Anterior", previous_rect, -1))
            if self.catalog_page < pages - 1:
                items.append(self._page_button(root, "Siguiente", next_rect, 1))

        self.catalog_items = items
        self._screen_items["catalog"] = items
        if self.screen == "catalog" and self.overlay is None:
            self.focus_items = self.sidebar_items + self.catalog_items
            default_key = focus_key or self._screen_focus_key.get("catalog")
            if default_key is None and entries:
                default_key = f"catalog:{entries[0].id}"
            self._set_focus_key(default_key or "filter:all", fallback=0)

    def _build_catalog_card(
        self,
        root: Any,
        entry: GameEntry,
        rect: Rect,
        items: list[FocusItem],
    ) -> None:
        selected = self.palette
        ring = ui.rounded(
            root,
            rect.grow(0.007),
            selected.accent,
            radius=17,
            bin_number=28,
            name="catalog-focus",
        )
        ring.hide()
        texture = art.game_art_texture(
            entry.id,
            "portrait",
            200,
            174,
            14,
            motif=entry.art_motif,
        )
        ui.image(root, texture, rect, bin_number=30)
        ui.image(
            root,
            art.circle_texture(24, selected.status if entry.installed else selected.muted),
            Rect(rect.x2 - 0.033, rect.x2 - 0.013, rect.z2 - 0.033, rect.z2 - 0.013),
            bin_number=32,
        )
        ui.text(
            root,
            entry.title.upper(),
            (rect.x1, rect.z1 - 0.050),
            0.031,
            selected.text,
            self.font_display,
            bin_number=60,
        )
        genre = entry.subtitle or entry.id
        ui.text(
            root,
            genre.upper(),
            (rect.x1, rect.z1 - 0.082),
            0.018,
            selected.muted,
            self.font_mono,
            bin_number=60,
        )
        button = self._hotspot(
            root,
            rect,
            partial(self._open_detail, entry),
            bin_number=34,
        )
        key = f"catalog:{entry.id}"
        self._bind_enter(button, partial(self._set_focus_key, key))

        def activate(entry: GameEntry = entry) -> None:
            self._open_detail(entry)

        items.append(
            FocusItem(
                key=key,
                rect=rect,
                ring=ring,
                activate=activate,
            )
        )

    def _page_button(self, root: Any, label: str, rect: Rect, delta: int) -> FocusItem:
        selected = self.palette
        ring = ui.rounded(
            root,
            rect.grow(0.005),
            selected.accent,
            radius=9,
            bin_number=28,
            name="page-focus",
        )
        ring.hide()
        rounded = ui.rounded(
            root,
            rect,
            theme.with_alpha(selected.raised, 0.80),
            radius=8,
            bin_number=30,
            name="page-button",
        )
        _ = rounded
        ui.text(
            root,
            label,
            (rect.center[0], rect.center[1] - 0.010),
            0.020,
            selected.text,
            self.font_mono,
            align=TextNode.ACenter,
            bin_number=60,
        )
        key = f"catalog:page:{delta}"
        button = self._hotspot(
            root,
            rect,
            partial(self._change_page, delta),
            bin_number=32,
        )
        self._bind_enter(button, partial(self._set_focus_key, key))
        return FocusItem(
            key=key,
            rect=rect,
            ring=ring,
            activate=partial(self._change_page, delta),
        )

    # -- overlays ------------------------------------------------------------

    def _build_overlays(self) -> None:
        selected = self.palette
        self.overlay_dim = DirectFrame(
            parent=self.overlay_root,
            frameColor=(0.0, 0.0, 0.0, 0.74),
            frameSize=(SCREEN.x1, SCREEN.x2, SCREEN.z1, SCREEN.z2),
            relief=DGG.FLAT,
        )
        self.overlay_dim.setBin("fixed", 100)

        self.launch_root = DirectFrame(
            parent=self.overlay_root,
            frameColor=selected.accent,
            frameSize=(SCREEN.x1, SCREEN.x2, SCREEN.z1, SCREEN.z2),
            relief=DGG.FLAT,
        )
        self.launch_root.setBin("fixed", 200)
        ui.text(
            self.launch_root,
            "ABRIENDO",
            (0.0, 0.170),
            0.034,
            selected.accent_ink,
            self.font_mono,
            align=TextNode.ACenter,
            bin_number=210,
        )
        self.launch_text = ui.text(
            self.launch_root,
            "",
            (0.0, 0.020),
            0.105,
            selected.accent_ink,
            self.font_display,
            align=TextNode.ACenter,
            bin_number=210,
        )
        ui.text(
            self.launch_root,
            "TOXINATOR",
            (0.0, -0.880),
            0.022,
            theme.with_alpha(selected.accent_ink, 0.65),
            self.font_mono,
            align=TextNode.ACenter,
            bin_number=210,
        )
        self.launch_root.hide()

    def _ensure_overlay(self, name: str) -> None:
        if name == "detail" and self.detail_root is None:
            self._build_detail_overlay()
        elif name == "controllers" and self.controllers_root is None:
            self._build_controllers_overlay()
        elif name == "settings" and self.settings_root is None:
            self._build_settings_overlay()
        elif name == "phone" and self.phone_root is None:
            self._build_phone_overlay()
        elif name == "quit" and self.quit_root is None:
            self._build_quit_overlay()

    def _overlay_panel(self, name: str, rect: Rect) -> Any:
        selected = self.palette
        root = self.overlay_root.attach_new_node(f"overlay-{name}")
        ui.rounded(
            root,
            rect.grow(0.008),
            theme.with_alpha(Vec4(0.0, 0.0, 0.0, 1.0), 0.40),
            radius=24,
            bin_number=104,
            name="panel-shadow",
        )
        ui.rounded(root, rect, selected.panel, radius=20, bin_number=105, name="panel")
        root.hide()
        return root

    def _build_detail_overlay(self) -> None:
        selected = self.palette
        rect = Rect(-1.18, 1.18, -0.700, 0.700)
        root = self._overlay_panel("detail", rect)
        self.detail_root = root
        items: list[FocusItem] = []

        art_rect = Rect(-1.11, -0.20, -0.630, 0.630)
        self.detail_widgets["art"] = ui.image(
            root,
            art.rounded_texture(400, 540, 18, selected.raised),
            art_rect,
            bin_number=110,
        )
        ui.text(
            root,
            "FICHA",
            (-0.12, 0.615),
            0.022,
            selected.accent,
            self.font_mono,
            bin_number=160,
        )
        self.detail_widgets["title"] = ui.text(
            root,
            "",
            (-0.12, 0.500),
            0.085,
            selected.text,
            self.font_display,
            bin_number=160,
        )
        self.detail_widgets["subtitle"] = ui.text(
            root,
            "",
            (-0.12, 0.415),
            0.022,
            selected.muted,
            self.font_mono,
            bin_number=160,
        )
        self.detail_widgets["description"] = ui.text(
            root,
            "",
            (-0.12, 0.325),
            0.032,
            selected.text,
            self.font_ui,
            bin_number=160,
        )
        self.detail_widgets["meta"] = ui.text(
            root,
            "",
            (-0.12, 0.045),
            0.026,
            selected.muted,
            self.font_mono,
            bin_number=160,
        )
        self.detail_widgets["state"] = ui.text(
            root,
            "",
            (-0.12, -0.170),
            0.026,
            selected.accent,
            self.font_mono,
            bin_number=160,
        )

        play_rect = Rect(0.28, 0.72, -0.610, -0.470)
        back_rect = Rect(0.77, 1.10, -0.610, -0.470)
        play_button, play_ring = ui.button(
            root,
            "Jugar",
            play_rect,
            selected.accent,
            selected.accent_ink,
            self.font_bold,
            self._detail_primary,
            text_scale=0.033,
            base_bin=150,
            ring_color=selected.text,
        )
        back_button, back_ring = ui.button(
            root,
            "Volver",
            back_rect,
            theme.with_alpha(selected.raised, 0.92),
            selected.text,
            self.font_bold,
            self._close_overlay,
            text_scale=0.029,
            base_bin=150,
            ring_color=selected.accent,
        )
        _ = (play_button, back_button)
        self.detail_widgets["play_label"] = play_button
        items.append(
            FocusItem(
                key="detail:play",
                rect=play_rect,
                ring=play_ring,
                activate=self._detail_primary,
            )
        )
        items.append(
            FocusItem(
                key="detail:close",
                rect=back_rect,
                ring=back_ring,
                activate=self._close_overlay,
            )
        )
        self._overlay_items["detail"] = items

    def _build_controllers_overlay(self) -> None:
        selected = self.palette
        rect = Rect(-0.96, 0.96, -0.680, 0.680)
        root = self._overlay_panel("controllers", rect)
        self.controllers_root = root
        items: list[FocusItem] = []
        ui.text(
            root,
            "MANDOS",
            (-0.88, 0.610),
            0.022,
            selected.accent,
            self.font_mono,
            bin_number=160,
        )
        ui.text(
            root,
            "Quién juega",
            (-0.88, 0.505),
            0.075,
            selected.text,
            self.font_display,
            bin_number=160,
        )
        ui.text(
            root,
            "Cada celular vinculado ocupa un lugar. La consola es el jugador 1.",
            (-0.88, 0.435),
            0.025,
            selected.muted,
            self.font_ui,
            bin_number=160,
        )
        self._controller_rows = []
        for slot in range(4):
            z2 = 0.330 - slot * 0.135
            row = Rect(-0.88, 0.88, z2 - 0.105, z2)
            ui.rounded(
                root,
                row,
                theme.with_alpha(selected.raised, 0.62),
                radius=12,
                bin_number=120,
                name="controller-row",
            )
            name = ui.text(
                root,
                "LIBRE",
                (row.x1 + 0.100, row.center[1] + 0.002),
                0.028,
                selected.text,
                self.font_bold,
                bin_number=160,
            )
            status = ui.text(
                root,
                "SIN MANDO",
                (row.x2 - 0.025, row.center[1] - 0.001),
                0.023,
                selected.muted,
                self.font_mono,
                align=TextNode.ARight,
                bin_number=160,
            )
            p_label = ui.text(
                root,
                f"P{slot + 1}",
                (row.x1 + 0.025, row.center[1] - 0.012),
                0.034,
                selected.accent,
                self.font_display,
                bin_number=161,
            )
            self._controller_rows.append((name, status, row, p_label))

        pair_rect = Rect(-0.88, -0.12, -0.600, -0.470)
        back_rect = Rect(0.00, 0.88, -0.600, -0.470)
        pair_button, pair_ring = ui.button(
            root,
            "Vincular celular",
            pair_rect,
            selected.accent,
            selected.accent_ink,
            self.font_bold,
            self._open_phone,
            text_scale=0.030,
            base_bin=150,
            ring_color=selected.text,
        )
        back_button, back_ring = ui.button(
            root,
            "Volver",
            back_rect,
            theme.with_alpha(selected.raised, 0.92),
            selected.text,
            self.font_bold,
            self._close_overlay,
            text_scale=0.030,
            base_bin=150,
            ring_color=selected.accent,
        )
        _ = (pair_button, back_button)
        items.append(
            FocusItem(
                key="controllers:pair",
                rect=pair_rect,
                ring=pair_ring,
                activate=self._open_phone,
            )
        )
        items.append(
            FocusItem(
                key="controllers:close",
                rect=back_rect,
                ring=back_ring,
                activate=self._close_overlay,
            )
        )
        self._overlay_items["controllers"] = items

    def _build_settings_overlay(self) -> None:
        selected = self.palette
        rect = Rect(-0.99, 0.99, -0.320, 0.580)
        root = self._overlay_panel("settings", rect)
        self.settings_root = root
        items: list[FocusItem] = []
        ui.text(
            root,
            "AJUSTES",
            (-0.90, 0.505),
            0.022,
            selected.accent,
            self.font_mono,
            bin_number=160,
        )
        ui.text(
            root,
            "Tu consola",
            (-0.90, 0.415),
            0.075,
            selected.text,
            self.font_display,
            bin_number=160,
        )
        ui.text(
            root,
            "Apariencia",
            (-0.90, 0.315),
            0.036,
            selected.text,
            self.font_bold,
            bin_number=160,
        )
        ui.text(
            root,
            "La consola usa una sola paleta en esta versión.",
            (-0.90, 0.278),
            0.023,
            selected.muted,
            self.font_ui,
            bin_number=160,
        )

        preview = Rect(-0.90, 0.90, 0.050, 0.245)
        ui.rounded(
            root,
            preview.grow(0.004),
            theme.with_alpha(selected.accent, 0.55),
            radius=14,
            bin_number=140,
            name="settings-preview-edge",
        )
        ui.rounded(
            root,
            preview,
            selected.bg,
            radius=12,
            bin_number=142,
            name="settings-preview",
        )
        ui.image(
            root,
            art.circle_texture(128, theme.with_alpha(selected.accent, 0.42)),
            Rect(preview.x2 - 0.170, preview.x2 + 0.020, preview.z2 - 0.170, preview.z2 + 0.020),
            bin_number=143,
        )
        ui.image(
            root,
            art.circle_texture(32, selected.accent),
            Rect(preview.x1 + 0.030, preview.x1 + 0.075, preview.z2 - 0.070, preview.z2 - 0.025),
            bin_number=145,
        )
        ui.text(
            root,
            selected.name,
            (preview.x1 + 0.095, preview.z2 - 0.060),
            0.032,
            selected.text,
            self.font_bold,
            bin_number=160,
        )
        ui.text(
            root,
            selected.note,
            (preview.x1 + 0.030, preview.z1 + 0.038),
            0.023,
            theme.with_alpha(selected.text, 0.82),
            self.font_mono,
            bin_number=160,
        )

        ui.text(
            root,
            "Idioma",
            (-0.90, -0.030),
            0.020,
            selected.muted,
            self.font_mono,
            bin_number=160,
        )
        ui.text(
            root,
            "Español",
            (-0.90, -0.072),
            0.024,
            selected.text,
            self.font_bold,
            bin_number=160,
        )
        ui.text(
            root,
            "Mandos",
            (0.10, -0.030),
            0.020,
            selected.muted,
            self.font_mono,
            bin_number=160,
        )
        ui.text(
            root,
            "P1–P4 desde Mandos",
            (0.10, -0.072),
            0.024,
            selected.text,
            self.font_bold,
            bin_number=160,
        )

        quit_rect = Rect(-0.90, -0.05, -0.250, -0.140)
        back_rect = Rect(0.14, 0.90, -0.250, -0.140)
        quit_button, quit_ring = ui.button(
            root,
            "Salir de Toxinator",
            quit_rect,
            theme.with_alpha(selected.raised, 0.92),
            selected.text,
            self.font_bold,
            self._open_quit,
            text_scale=0.029,
            base_bin=150,
            ring_color=selected.accent,
        )
        back_button, back_ring = ui.button(
            root,
            "Volver",
            back_rect,
            selected.accent,
            selected.accent_ink,
            self.font_bold,
            self._close_overlay,
            text_scale=0.030,
            base_bin=150,
            ring_color=selected.text,
        )
        _ = (quit_button, back_button)
        items.append(
            FocusItem(
                key="settings:quit",
                rect=quit_rect,
                ring=quit_ring,
                activate=self._open_quit,
            )
        )
        items.append(
            FocusItem(
                key="settings:close",
                rect=back_rect,
                ring=back_ring,
                activate=self._close_overlay,
            )
        )
        self._overlay_items["settings"] = items

    def _build_phone_overlay(self) -> None:
        selected = self.palette
        rect = Rect(-1.02, 1.02, -0.720, 0.720)
        root = self._overlay_panel("phone", rect)
        self.phone_root = root
        items: list[FocusItem] = []
        self.phone_widgets["kicker"] = ui.text(
            root,
            "VINCULAR MANDO",
            (-0.94, 0.640),
            0.024,
            selected.accent,
            self.font_mono,
            bin_number=160,
        )
        self.phone_widgets["title"] = ui.text(
            root,
            "Escaneá el QR",
            (-0.94, 0.530),
            0.075,
            selected.text,
            self.font_display,
            bin_number=160,
        )
        self.phone_widgets["body"] = ui.text(
            root,
            "Misma Wi-Fi que la consola.\nAbrí el enlace en el navegador del celular.",
            (-0.94, 0.390),
            0.028,
            selected.text,
            self.font_ui,
            bin_number=160,
        )
        self.phone_widgets["url"] = ui.text(
            root,
            "",
            (-0.94, 0.240),
            0.021,
            selected.accent,
            self.font_mono,
            bin_number=160,
        )
        self.phone_widgets["status"] = ui.text(
            root,
            "ESPERANDO CELULAR…",
            (-0.94, -0.240),
            0.022,
            selected.status,
            self.font_mono,
            bin_number=160,
        )
        self.qr_image = OnscreenImage(
            image=qr_texture(self, self.phone_url),
            parent=root,
            pos=(0.45, 0.0, 0.060),
            scale=(0.390, 1.0, 0.390),
        )
        self.qr_image.setBin("fixed", 155)
        back_rect = Rect(-0.94, -0.05, -0.620, -0.490)
        back_button, back_ring = ui.button(
            root,
            "Volver",
            back_rect,
            theme.with_alpha(selected.raised, 0.92),
            selected.text,
            self.font_bold,
            self._close_overlay,
            text_scale=0.030,
            base_bin=150,
            ring_color=selected.accent,
        )
        _ = back_button
        items.append(
            FocusItem(
                key="phone:close",
                rect=back_rect,
                ring=back_ring,
                activate=self._close_overlay,
            )
        )
        self._overlay_items["phone"] = items

    def _build_quit_overlay(self) -> None:
        selected = self.palette
        rect = Rect(-0.560, 0.560, -0.370, 0.370)
        root = self._overlay_panel("quit", rect)
        self.quit_root = root
        items: list[FocusItem] = []
        ui.text(
            root,
            "SALIR",
            (-0.49, 0.300),
            0.020,
            selected.accent,
            self.font_mono,
            bin_number=160,
        )
        ui.text(
            root,
            "¿Apagar Toxinator?",
            (-0.49, 0.190),
            0.052,
            selected.text,
            self.font_display,
            bin_number=160,
        )
        ui.text(
            root,
            "Enter para cerrar. Esc para volver.",
            (-0.49, 0.120),
            0.026,
            selected.muted,
            self.font_ui,
            bin_number=160,
        )
        quit_rect = Rect(-0.49, -0.05, -0.280, -0.160)
        back_rect = Rect(0.08, 0.49, -0.280, -0.160)
        quit_button, quit_ring = ui.button(
            root,
            "Apagar",
            quit_rect,
            selected.accent,
            selected.accent_ink,
            self.font_bold,
            self._quit,
            text_scale=0.032,
            base_bin=150,
            ring_color=selected.text,
        )
        back_button, back_ring = ui.button(
            root,
            "Volver",
            back_rect,
            theme.with_alpha(selected.raised, 0.92),
            selected.text,
            self.font_bold,
            self._close_overlay,
            text_scale=0.028,
            base_bin=150,
            ring_color=selected.accent,
        )
        _ = (quit_button, back_button)
        items.append(
            FocusItem(
                key="quit:yes",
                rect=quit_rect,
                ring=quit_ring,
                activate=self._quit,
            )
        )
        items.append(
            FocusItem(
                key="quit:no",
                rect=back_rect,
                ring=back_ring,
                activate=self._close_overlay,
            )
        )
        self._overlay_items["quit"] = items

    def _hud_frame(self, selected: theme.Palette) -> None:
        segments = LineSegs("sidebar-hud")
        segments.setColor(theme.with_alpha(selected.raised, 0.58))
        segments.setThickness(1.2)
        # Angular HUD frame around the clock and controller area.
        segments.moveTo(-1.70, 0.0, -0.28)
        segments.drawTo(-1.70, 0.0, -0.94)
        segments.drawTo(-1.14, 0.0, -0.94)
        segments.moveTo(-1.70, 0.0, -0.28)
        segments.drawTo(-1.60, 0.0, -0.28)
        segments.moveTo(-1.14, 0.0, -0.94)
        segments.drawTo(-1.14, 0.0, -0.84)
        segments.moveTo(-1.70, 0.0, -0.36)
        segments.drawTo(-1.64, 0.0, -0.42)
        segments.moveTo(-1.46, 0.0, -0.94)
        segments.drawTo(-1.40, 0.0, -0.88)
        for z in (-0.55, -0.68, -0.81):
            segments.moveTo(-1.70, 0.0, z)
            segments.drawTo(-1.665, 0.0, z)
        node = self.ui_root.attach_new_node(segments.create())
        node.setBin("fixed", 7)
        node.setDepthTest(False)

    # -- state / focus -------------------------------------------------------

    def _show_screen(self, screen: str, *, restore: bool = False) -> None:
        if screen not in ("home", "catalog"):
            screen = "home"
        self.screen = screen
        if self.home_root is not None:
            self.home_root.show() if screen == "home" else self.home_root.hide()
        if self.catalog_root is not None:
            self.catalog_root.show() if screen == "catalog" else self.catalog_root.hide()
        self._refresh_nav()
        self.focus_items = self.sidebar_items + self._screen_items.get(screen, [])
        if screen == "catalog":
            items = self._screen_items.get("catalog", [])
            default = self._screen_focus_key.get("catalog")
            if default is None and items:
                default = next(
                    (item.key for item in items if item.key.startswith("catalog:")),
                    items[0].key,
                )
            self._set_focus_key(default or "nav:catalog", fallback=0)
        else:
            default = self._screen_focus_key.get("home")
            if default is None and self.shelf_entries:
                default = f"shelf:{self.shelf_entries[0].id}"
            self._set_focus_key(default or "hero:play", fallback=0)
        if restore:
            self._last_focus_key = ""

    def _refresh_nav(self) -> None:
        selected = self.palette
        active = "home" if self.screen == "home" else "catalog"
        if self.overlay in ("controllers",):
            active = "controllers"
        elif self.overlay in ("settings",):
            active = "settings"
        for key, visual in self.nav_visuals.items():
            is_active = key == active
            visual["background"].show() if is_active else visual["background"].hide()
            visual["marker"].show() if is_active else visual["marker"].hide()
            visual["label"].setFg(selected.text if is_active else selected.muted)
            visual["icon"].setColorScale(selected.text if is_active else selected.muted)

    def _set_focus_key(self, key: str | None, fallback: int | None = None) -> None:
        if key is not None:
            for index, item in enumerate(self.focus_items):
                if item.key == key:
                    self.focus_index = index
                    self._refresh_focus()
                    return
        if fallback is not None and self.focus_items:
            self.focus_index = max(0, min(fallback, len(self.focus_items) - 1))
            self._refresh_focus()

    def _refresh_focus(self) -> None:
        for index, item in enumerate(self.focus_items):
            if item.ring is None:
                continue
            if index == self.focus_index:
                item.ring.show()
            else:
                item.ring.hide()
        if not self.focus_items:
            return
        current = self.focus_items[self.focus_index]
        self._last_focus_key = current.key
        if current.on_focus is not None:
            current.on_focus()
        if self.overlay is None:
            self._screen_focus_key[self.screen] = current.key

    def _move_focus(self, dx: int, dy: int) -> None:
        if self.state != "launcher" or not self.focus_items:
            return
        if self.overlay == "launching":
            return
        current = self.focus_items[self.focus_index]
        current_x, current_z = current.rect.center
        best_index = -1
        best_score = 1e9
        for index, item in enumerate(self.focus_items):
            if index == self.focus_index:
                continue
            item_x, item_z = item.rect.center
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

    def _focus_entry(self, entry: GameEntry) -> None:
        if self.hero_entry is entry:
            return
        self.hero_entry = entry
        self._refresh_hero()

    def _refresh_hero(self) -> None:
        if not self._hero_widgets:
            return
        selected = self.palette
        entry = self.hero_entry
        art_widget = self._hero_widgets.get("art")
        if entry is None:
            if art_widget is not None:
                ui.swap_image(
                    art_widget,
                    art.rounded_texture(560, 236, 20, selected.raised),
                )
            self._hero_widgets["eyebrow"].setText("SIN JUEGOS")
            self._hero_widgets["title"].setText("Todavía no hay juegos")
            self._hero_widgets["title"].setScale(0.075)
            self._hero_widgets["subtitle"].setText("AGREGÁ UN JUEGO Y REINICIÁ LA CONSOLA")
            self._hero_widgets["description"].setText(
                "La biblioteca está vacía. Instalá un juego externo para verlo acá."
            )
            for _rect, label in self._hero_widgets.get("pills", []):
                label.setText("")
            self._hero_widgets["play_label"].configure(text="Sin juegos")
            return
        if art_widget is not None:
            ui.swap_image(
                art_widget,
                art.game_art_texture(
                    entry.id,
                    "hero",
                    560,
                    236,
                    20,
                    motif=entry.art_motif,
                ),
            )
        self._hero_widgets["eyebrow"].setText(
            "LISTO PARA JUGAR" if entry.installed else "PRÓXIMAMENTE"
        )
        title_widget = self._hero_widgets["title"]
        title_widget.setText(entry.title.upper())
        title_widget.setScale(0.120 if len(entry.title) <= 16 else 0.098)
        self._hero_widgets["subtitle"].setText(entry.subtitle.upper())
        self._hero_widgets["description"].setText(ui.wrap(entry.description, 62))

        players = (
            f"{entry.players[0]} JUGADOR"
            if entry.players[0] == entry.players[1]
            else f"{entry.players[0]}–{entry.players[1]} JUGADORES"
        )
        modes = (
            f"{len(entry.modes)} FORMATO"
            if len(entry.modes) == 1
            else f"{len(entry.modes)} FORMATOS"
        )
        state = "INSTALADO" if entry.installed else "EN EL CATÁLOGO"
        labels = (players, modes, state)
        for (_rect, label), value in zip(self._hero_widgets.get("pills", []), labels, strict=False):
            label.setText(value)
            label.setFg(selected.status if value == "INSTALADO" else selected.text)

        play_label = self._hero_widgets.get("play_label")
        if play_label is not None:
            play_label.configure(
                text="Jugar" if entry.installed else "Ver ficha",
                text_fg=selected.accent_ink,
            )

    # -- actions -------------------------------------------------------------

    def _nav_activate(self, key: str) -> None:
        if key in ("home", "catalog"):
            self._show_screen(key)
            return
        if key == "controllers":
            self._open_controllers()
            return
        if key == "settings":
            self._open_settings()

    def _activate(self) -> None:
        logger.info(
            "activate state=%s screen=%s overlay=%s focus=%s",
            self.state,
            self.screen,
            self.overlay,
            self._last_focus_key,
        )
        if self.state == "game" or self.overlay == "launching":
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
        if self.screen == "catalog":
            self._show_screen("home")
            return
        self._open_quit()

    def _check_phone_back(self, state: InputState) -> bool:
        b_pressed = any(item.button("circle") for item in state.frames.values())
        triggered = b_pressed and not self._last_b
        self._last_b = b_pressed
        if triggered:
            self._phone_back()
        return triggered

    def _phone_back(self) -> None:
        logger.info("phone back state=%s overlay=%s", self.state, self.overlay)
        if self.state == "game":
            self._return_to_launcher()
            return
        if self.overlay == "launching":
            self._cancel_launch()
            return
        if self.overlay is not None:
            self._close_overlay()
            return
        if self.screen == "catalog":
            self._show_screen("home")
            return
        if self.focus_items:
            self._set_focus_key("hero:play", fallback=0)

    def _launch_hero(self) -> None:
        if self.hero_entry is None:
            return
        if not self.hero_entry.installed:
            self._open_detail(self.hero_entry)
            return
        self._start_launch(self.hero_entry)

    def _open_detail_from_focus(self) -> None:
        if self.hero_entry is not None:
            self._open_detail(self.hero_entry)
            return
        if self.focus_items:
            current = self.focus_items[self.focus_index]
            entry_id = current.key.split(":", 1)[1] if current.key.startswith("shelf:") else None
            entry = self._entry(entry_id)
            if entry is not None:
                self._open_detail(entry)

    def _open_detail(self, entry: GameEntry) -> None:
        if self.state != "launcher":
            return
        self._ensure_overlay("detail")
        self.detail_entry = entry
        ui.swap_image(
            self.detail_widgets["art"],
            art.game_art_texture(
                entry.id,
                "portrait",
                300,
                405,
                16,
                motif=entry.art_motif,
            ),
        )
        self.detail_widgets["title"].setText(entry.title.upper())
        self.detail_widgets["subtitle"].setText(entry.subtitle.upper())
        self.detail_widgets["description"].setText(ui.wrap(entry.description, 48))
        players = (
            f"{entry.players[0]}"
            if entry.players[0] == entry.players[1]
            else f"{entry.players[0]}–{entry.players[1]}"
        )
        modes = ", ".join(entry.modes) if entry.modes else "—"
        self.detail_widgets["meta"].setText(
            f"JUGADORES   {players}\n"
            f"FORMATOS    {modes}\n"
            f"ID          {entry.id}"
        )
        state_text = "INSTALADO Y LISTO" if entry.installed else "TODAVÍA NO ESTÁ INSTALADO"
        self.detail_widgets["state"].setText(state_text)
        self.detail_widgets["state"].setFg(
            self.palette.status if entry.installed else self.palette.accent
        )
        self.detail_widgets["play_label"].configure(
            text="Jugar" if entry.installed else "Volver al catálogo",
            text_fg=self.palette.accent_ink if entry.installed else self.palette.muted,
        )
        self._open_overlay("detail", focus_key="detail:play" if entry.installed else "detail:close")

    def _detail_primary(self) -> None:
        if self.detail_entry is None:
            return
        if self.detail_entry.installed:
            self._start_launch(self.detail_entry)
        else:
            self._close_overlay()

    def _pick_filter(self, filter_id: str) -> None:
        self.catalog_filter = filter_id
        self.catalog_page = 0
        self._rebuild_catalog_dynamic(focus_key=f"filter:{filter_id}")

    def _change_page(self, delta: int) -> None:
        pages = self._page_count()
        self.catalog_page = max(0, min(self.catalog_page + delta, pages - 1))
        entries = self._page_entries()
        focus_key = f"catalog:{entries[0].id}" if entries else None
        self._rebuild_catalog_dynamic(focus_key=focus_key)

    def _open_overlay(self, name: str, *, focus_key: str | None = None) -> None:
        if self.state != "launcher":
            return
        self._ensure_overlay(name)
        self.overlay = name
        self.overlay_root.show()
        for root_name in (
            "detail_root",
            "controllers_root",
            "settings_root",
            "phone_root",
            "quit_root",
            "launch_root",
        ):
            root = getattr(self, root_name, None)
            if root is not None:
                root.hide()
        roots = {
            "detail": self.detail_root,
            "controllers": self.controllers_root,
            "settings": self.settings_root,
            "phone": self.phone_root,
            "quit": self.quit_root,
        }
        target = roots.get(name)
        if target is not None:
            target.show()
        if name == "phone":
            self._prepare_phone_overlay()
        if name == "controllers":
            self._refresh_controllers_from_hub()
        self.focus_items = self._overlay_items.get(name, [])
        if name in ("settings", "controllers"):
            self._refresh_nav()
        default_key = focus_key or (self.focus_items[0].key if self.focus_items else None)
        self._set_focus_key(default_key, fallback=0)

    def _close_overlay(self) -> None:
        if self.overlay == "phone" and not self._has_controller:
            self._pairing_dismissed = True
        self._phone_waiting = False
        self.overlay = None
        self.overlay_root.hide()
        self.focus_items = self.sidebar_items + self._screen_items.get(self.screen, [])
        self._refresh_nav()
        self._set_focus_key(self._screen_focus_key.get(self.screen), fallback=0)

    def _open_controllers(self) -> None:
        self._open_overlay("controllers")

    def _open_settings(self) -> None:
        if self.state != "launcher":
            return
        self._open_overlay("settings", focus_key="settings:close")

    def _open_quit(self) -> None:
        if self.state != "launcher":
            return
        self._open_overlay("quit")

    def _prepare_phone_overlay(self) -> None:
        selected = self.palette
        if self.phone_widgets:
            waiting = not self._has_controller
            self.phone_widgets["kicker"].setText(
                "VINCULAR MANDO" if waiting else "SUMAR CELULAR"
            )
            self.phone_widgets["title"].setText(
                "Escaneá para entrar" if waiting else "Escaneá el QR"
            )
            if waiting:
                body = (
                    "No hay ningún mando conectado.\n"
                    + (
                        "Escaneá el QR con la cámara del celular.\n"
                        "Aceptá el certificado y esta pantalla se cierra sola."
                        if self.phone_secure
                        else "Escaneá el QR con la cámara del celular.\n"
                        "Abrí el enlace y esta pantalla se cierra sola."
                    )
                )
            else:
                body = (
                    "Misma Wi-Fi que la consola.\n"
                    + (
                        "Aceptá el certificado autofirmado una vez."
                        if self.phone_secure
                        else "Abrí la URL en el navegador del celular."
                    )
                )
            self.phone_widgets["body"].setText(body)
            self.phone_widgets["url"].setText(ui.wrap(self.phone_url, 40))
            self.phone_widgets["status"].setText(
                "ESPERANDO CELULAR…"
                if self.phone_secure
                else "MODO HTTP · ESPERANDO CELULAR…"
            )
            self.phone_widgets["status"].setFg(selected.status)

    def _open_phone(self, *, waiting: bool | None = None) -> None:
        if self.state != "launcher":
            return
        if waiting is None:
            waiting = not self._has_controller
        self._phone_waiting = waiting
        self._pairing_dismissed = False
        self._open_overlay("phone", focus_key="phone:close")

    def _start_launch(self, entry: GameEntry) -> None:
        logger.info("start launch %s", entry.id)
        if not entry.installed:
            self._open_detail(entry)
            return
        self._set_game_assets_callback(entry.id, entry.assets_root)
        self._notify_controller(self._controller_profile(entry))
        self.pending = entry
        self.launch_timer = 0.7
        self.overlay = "launching"
        self.overlay_root.show()
        self.overlay_dim.hide()
        for root_name in (
            "detail_root",
            "controllers_root",
            "settings_root",
            "phone_root",
            "quit_root",
        ):
            root = getattr(self, root_name, None)
            if root is not None:
                root.hide()
        if self.launch_text is not None:
            self.launch_text.setText(entry.title.upper())
        if self.launch_root is not None:
            self.launch_root.show()

    def _cancel_launch(self) -> None:
        self.pending = None
        self.overlay = None
        self._set_game_assets_callback("", None)
        self._notify_controller(None)
        if self.launch_root is not None:
            self.launch_root.hide()
        self.overlay_root.hide()
        self.overlay_dim.show()
        self.focus_items = self.sidebar_items + self._screen_items.get(self.screen, [])
        self._refresh_focus()

    def _start_game(self, entry: GameEntry) -> None:
        logger.info("start game %s", entry.id)
        self._set_game_assets_callback(entry.id, entry.assets_root)
        try:
            game: Game = entry.instantiate()
        except Exception as error:
            logger.exception("no pude cargar %s", entry.id)
            if self.launch_text is not None:
                self.launch_text.setText(f"ERROR: {error}")
            self.launch_timer = 2.0
            return
        try:
            self.host = GameHost(self, game, self.hub, phone=self.phone)
            self.host.start()
        except Exception as error:
            logger.exception("no pude iniciar %s", entry.id)
            if self.host is not None:
                self.host.stop()
                self.host = None
            if self.launch_text is not None:
                self.launch_text.setText(f"ERROR: {error}")
            self.launch_timer = 2.0
            return
        self.state = "game"
        self.overlay = None
        self.pending = None
        self._notify_controller(self._controller_profile(entry))
        self._notify_mode("game")
        self.ui_root.hide()
        self.overlay_root.hide()
        self.overlay_dim.show()

    def _return_to_launcher(self) -> None:
        if self.host is not None:
            self.host.stop()
            self.host = None
        self.state = "launcher"
        self.overlay = None
        self._set_game_assets_callback("", None)
        self._notify_controller(None)
        self._notify_mode("launcher")
        self.ui_root.show()
        self.overlay_root.hide()
        self.overlay_dim.show()
        self.setBackgroundColor(self.palette.bg)
        self.focus_items = self.sidebar_items + self._screen_items.get(self.screen, [])
        self._refresh_nav()
        self._set_focus_key(
            self._screen_focus_key.get(self.screen),
            fallback=0,
        )

    def _quit(self) -> None:
        self._exit()

    # -- frame ---------------------------------------------------------------

    def _update(self, task: Any) -> Any:
        dt = min(max(globalClock.getDt(), 0.0), 0.1)
        now = time.monotonic()
        self._refresh_clock(datetime.now())

        if self.state == "game":
            if self.host is not None:
                self.host.update(dt)
                self._check_phone_back(self.host.ctx.input_state)
        else:
            state = self.hub.poll()
            self._update_controllers(state)
            frame = state.primary_frame()
            self._update_joystick(frame, dt)
            back_triggered = self._check_phone_back(state)
            a_pressed = any(item.button("cross") for item in state.frames.values())
            if not back_triggered and a_pressed and not self._last_a:
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
        if self.overlay == "launching" or self.state != "launcher" or frame is None:
            self._joy_dir = None
            self._joy_hold = 0.0
            self._joy_repeat = 0.0
            return
        dx = frame.axis("move_x")
        dy = frame.axis("move_y")
        if abs(dx) < 0.0001 and abs(dy) < 0.0001:
            if frame.pointer is None:
                self._joy_dir = None
                self._joy_hold = 0.0
                self._joy_repeat = 0.0
                return
            dx = frame.pointer[0] - 0.5
            dy = 0.5 - frame.pointer[1]
        if math.hypot(dx, dy) < 0.22:
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
        mouse_hover = not frame.touch and frame.controller_id.startswith("keyboard")
        if mouse_hover:
            return
        self._joy_hold += dt
        if self._joy_hold >= 0.35:
            self._joy_repeat += dt
            if self._joy_repeat >= 0.16:
                self._joy_repeat = 0.0
                self._move_focus(*direction)

    def _refresh_clock(self, now: datetime) -> None:
        value = f"{now.hour:02d}:{now.minute:02d}"
        if value == self._last_clock:
            return
        self._last_clock = value
        if self._clock_text is not None:
            self._clock_text.setText(value)
        if self._date_text is not None:
            self._date_text.setText(
                f"{WEEKDAYS[now.weekday()]} {now.day} de {MONTHS[now.month - 1]}"
            )

    def _refresh_controllers_empty(self) -> None:
        selected = self.palette
        if self._controller_summary is not None:
            self._controller_summary.setText("MANDOS 0/4")
            self._controller_summary.setFg(selected.muted)
        for dot, label, _rect in self._controller_chips:
            dot.setColor(selected.muted)
            label.setFg(selected.muted)
        for name, status, _row, p_label in self._controller_rows:
            name.setText("LIBRE")
            name.setFg(selected.text)
            status.setText("SIN MANDO")
            status.setFg(selected.muted)
            p_label.setFg(selected.muted)
    def _refresh_controllers_from_hub(self) -> None:
        if self.hub is not None:
            self._update_controllers(self.hub.poll())

    def _update_controllers(self, state: InputState) -> None:
        selected = self.palette
        connected = 0
        for slot, (dot, label, _rect) in enumerate(self._controller_chips):
            info = state.controller(slot)
            live = state.frame(slot)
            if live is not None:
                connected += 1
                color = selected.status
                label.setText(f"P{slot + 1}")
            elif info is not None:
                color = selected.accent
                label.setText(f"P{slot + 1}")
            else:
                color = selected.muted
                label.setText(f"P{slot + 1}")
            dot.setColor(color)
            label.setFg(color)

        if self._controller_summary is not None:
            primary = state.primary_controller()
            simplex = " · TECLADO" if primary is not None and primary.source == "sim" else ""
            self._controller_summary.setText(f"MANDOS {connected}/4{simplex}")
            self._controller_summary.setFg(
                selected.status if connected or simplex else selected.muted
            )

        for slot, (name, status, _row, p_label) in enumerate(self._controller_rows):
            info = state.controller(slot)
            live = state.frame(slot)
            if live is not None:
                display = info.display_name if info is not None else f"Celular P{slot + 1}"
                name.setText(display.upper())
                name.setFg(selected.text)
                status.setText("LISTO")
                status.setFg(selected.status)
                p_label.setFg(selected.status)
            elif info is not None:
                name.setText(info.display_name.upper() if info.display_name else f"P{slot + 1}")
                name.setFg(selected.text)
                status.setText("EN GRACIA")
                status.setFg(selected.accent)
                p_label.setFg(selected.accent)
            else:
                name.setText("LIBRE")
                name.setFg(selected.text)
                status.setText("SIN MANDO")
                status.setFg(selected.muted)
                p_label.setFg(selected.muted)

        self._update_pairing(any(state.frame(slot) is not None for slot in range(4)))

    def _update_pairing(self, has_controller: bool) -> None:
        self._has_controller = has_controller
        if has_controller:
            self._pairing_dismissed = False
            if self.overlay == "phone" and self._phone_waiting:
                self._last_a = True
                self._close_overlay()
            return
        if self.overlay is None and not self._pairing_dismissed:
            self._open_phone(waiting=True)

    def _notify_mode(self, mode: str) -> None:
        logger.info("launcher mode %s", mode)
        self._set_mode_callback(mode)

    def _controller_profile(self, entry: GameEntry) -> dict[str, Any]:
        labels = dict(entry.controller_labels)
        panel = (
            entry.controller_panel.as_dict()
            if entry.controller_panel is not None
            else None
        )
        return {
            "layout": entry.controller_layout,
            "skin": entry.controller_skin,
            "orientation": entry.controller_orientation,
            "buttons": ["cross", "circle", "square", "triangle", "options", "l1", "r1"],
            "labels": labels,
            "action": labels.get("cross", entry.controller_action),
            "back": labels.get("circle", entry.controller_back),
            "hint": entry.controller_hint,
            "camera": entry.controller_camera,
            "panel": panel,
            "game": entry.title,
        }

    def _notify_controller(self, profile: dict[str, Any] | None) -> None:
        logger.info(
            "launcher controller %s",
            "reset" if profile is None else profile.get("layout"),
        )
        self._set_controller_callback(profile)

    def _exit(self) -> None:
        if self.host is not None:
            self.host.stop()
            self.host = None
        self.userExit()
