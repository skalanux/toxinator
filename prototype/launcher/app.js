"use strict";

/* ------------------------------------------------------------------ */
/* Data                                                                */
/* ------------------------------------------------------------------ */

const VARIANTS = ["A", "B", "C"];
const VARIANT_NAMES = { A: "Carousel", B: "Biblioteca", C: "Mosaico" };
const THEMES = ["feria", "comic", "neon"];
const THEME_NAMES = {
  feria: "Feria",
  comic: "Cómic",
  neon: "Neón",
};
const THEME_TAGLINES = {
  feria: "LA FERIA MALDITA",
  comic: "CÓMIC DE BARRIO",
  neon: "NEÓN",
};
const QUALITY_LEVELS = {
  es: ["Baja", "Media", "Alta"],
  en: ["Low", "Medium", "High"],
};
const TEXT_SCALES = [90, 100, 110, 125];
const SETTING_KEYS = [
  "language",
  "master",
  "music",
  "sfx",
  "quality",
  "textScale",
  "controllers",
];

const GAMES = [
  {
    id: "maldito-pino",
    title: "Maldito Pino",
    subtitle: "hijo de pu**",
    installed: true,
    accent: "#33d6e6",
    icon: "pin",
    players: [1, 4],
    version: "1.0.0",
    requires: ["motion", "buttons"],
    modes: [
      {
        id: "match",
        name: { es: "Partida", en: "Match" },
        desc: {
          es: "10 turnos, pleno/spare y desempate por muerte súbita.",
          en: "10 frames, strikes/spares and sudden-death tie-break.",
        },
      },
      {
        id: "practice",
        name: { es: "Práctica", en: "Practice" },
        desc: {
          es: "Tiros ilimitados, sin puntaje, para calibrar el swing.",
          en: "Unlimited throws, no scoring, to tune the swing.",
        },
      },
    ],
    description: {
      es: "Bolos con pinos que provocan. Una pista, 1–4 jugadores y un marcador que se pone picante.",
      en: "Bowling with trash-talking pins. One lane, 1–4 players, and a scoreboard with attitude.",
    },
  },
  {
    id: "kart",
    title: "Kart",
    subtitle: "próximamente",
    installed: false,
    accent: "#ff8a3d",
    icon: "kart",
    players: [1, 4],
    version: "—",
    requires: ["motion", "buttons"],
    modes: [
      {
        id: "race",
        name: { es: "Carrera", en: "Race" },
        desc: {
          es: "Split-screen arcade, drift y vueltas.",
          en: "Arcade split-screen, drift and laps.",
        },
      },
    ],
    description: {
      es: "Carreras arcade para el living. Todavía no está instalado.",
      en: "Arcade racing for the living room. Not installed yet.",
    },
  },
  {
    id: "tenis",
    title: "Tenis",
    subtitle: "próximamente",
    installed: false,
    accent: "#8ef07a",
    icon: "tennis",
    players: [1, 4],
    version: "—",
    requires: ["motion", "buttons"],
    modes: [
      {
        id: "match",
        name: { es: "Partida", en: "Match" },
        desc: {
          es: "Swing, pelota y efecto.",
          en: "Swing, ball and spin.",
        },
      },
    ],
    description: {
      es: "Tenis de swing con raqueta y pelota. Todavía no está instalado.",
      en: "Swing tennis with racket and ball. Not installed yet.",
    },
  },
];

const DEFAULT_CONTROLLERS = [
  {
    slot: 1,
    type: "android",
    name: "Pixel 8",
    connected: true,
    caps: ["motion", "buttons", "touch"],
    battery: 78,
  },
  {
    slot: 2,
    type: "wiimote",
    name: "Wii Remote",
    connected: false,
    caps: ["motion", "buttons"],
    battery: null,
    note: { es: "sin pilas", en: "no batteries" },
  },
  {
    slot: 3,
    type: "gamepad",
    name: "Gamepad",
    connected: true,
    caps: ["buttons", "axes"],
    battery: null,
  },
  {
    slot: 4,
    type: null,
    name: "",
    connected: false,
    caps: [],
    battery: null,
  },
];

const I18N = {
  es: {
    home: "Inicio",
    library: "Biblioteca",
    settings: "Ajustes",
    players: "Jugadores",
    play: "Jugar",
    launch: "Iniciar",
    back: "Volver",
    done: "Listo",
    close: "Cerrar",
    select: "Seleccionar",
    navigate: "Navegar",
    variant: "Variante",
    theme: "Tema",
    help: "Ayuda",
    installed: "Instalado",
    notInstalled: "No instalado",
    comingSoon: "Próximamente",
    playersShort: "jugadores",
    player: "Jugador",
    modes: "Modos",
    version: "Versión",
    requiredCaps: "Capacidades requeridas",
    gameDetails: "Detalle del juego",
    chooseMode: "Elegí un modo",
    ready: "Listo para jugar",
    noController: "Falta un mando compatible",
    connectPhone: "Conectar teléfono",
    simulateJoin: "Simular join",
    connecting: "Conectar teléfono",
    scanQr: "Escaneá el QR desde el celular",
    qrMock: "QR de ejemplo (mock)",
    searching: "Buscando mandos…",
    simulateConnect: "Simular conexión",
    cancel: "Cancelar",
    quit: "Apagar",
    quitQuestion: "¿Apagar Toxinator 3?",
    quitBody: "Se cierra la partida y volvés al sistema. En el prototipo, la consola se apagaría.",
    powerOff: "Apagar",
    offTitle: "Toxinator 3 se apagaría",
    offBody: "Enter o Esc para volver al prototipo.",
    errorTitle: "No se puede iniciar",
    errorDemo: "Error de capacidades",
    errorBody:
      "Maldito Pino necesita movimiento y botones. El mando 3 (Gamepad) no tiene movimiento.",
    reassign: "Reasignar mando",
    emptyTitle: "Biblioteca vacía",
    emptyBody:
      "No hay juegos instalados. En la consola final, acá aparecerían los juegos descubiertos por manifest/entry point.",
    emptyBack: "Volver",
    helpTitle: "Prototipo de launcher",
    helpIntro:
      "Tres variantes de UI para reaccionar. No es el launcher final: la implementación va a ser Panda3D/DirectGUI.",
    language: "Idioma",
    languageDesc: "Cambia los textos de la consola.",
    spanish: "Español",
    english: "English",
    master: "Volumen general",
    music: "Música",
    sfx: "Efectos",
    quality: "Calidad gráfica",
    textScale: "Escala de texto",
    controllers: "Mandos",
    controllersDesc: "Asignar, conectar o liberar mandos.",
    manageControllers: "Gestionar",
    connected: "Conectado",
    disconnected: "Desconectado",
    emptySlot: "Slot vacío",
    assign: "Cambiar mando",
    battery: "Batería",
    noBattery: "Sin batería",
    warningCaps: "No cumple las capacidades del juego",
    gamepad: "Gamepad",
    phone: "Celular Android",
    wiimote: "Wiimote",
    currentState: "Estado actual",
    prototypeNote: "Barra de prototipo: cambia de variante sin salir del estado.",
    playerSlot: "Jugador",
    change: "Cambiar",
    closeHelp: "Cerrar ayuda",
    mode: "Modo",
    noModes: "Sin modos",
    joinHelp: "J: simular join · C: conectar teléfono · Enter: cambiar mando",
    settingsHelp: "↑↓: fila · ←→: valor · Enter: gestionar mandos · Esc: volver",
    playersHelp: "←→: slot · Enter: cambiar mando · J: join · C: teléfono · Esc: volver",
    backHome: "Volver al inicio",
    launching: "Iniciando",
    launchReady: "Listo. El juego se habría abierto.",
    backToLauncher: "Volver al launcher",
    titleFull: "Título completo",
    variantHint: "V cambia de variante · H ayuda",
  },
  en: {
    home: "Home",
    library: "Library",
    settings: "Settings",
    players: "Players",
    play: "Play",
    launch: "Launch",
    back: "Back",
    done: "Done",
    close: "Close",
    select: "Select",
    navigate: "Navigate",
    variant: "Variant",
    theme: "Theme",
    help: "Help",
    installed: "Installed",
    notInstalled: "Not installed",
    comingSoon: "Coming soon",
    playersShort: "players",
    player: "Player",
    modes: "Modes",
    version: "Version",
    requiredCaps: "Required capabilities",
    gameDetails: "Game details",
    chooseMode: "Choose a mode",
    ready: "Ready to play",
    noController: "No compatible controller",
    connectPhone: "Connect phone",
    simulateJoin: "Simulate join",
    connecting: "Connect phone",
    scanQr: "Scan the QR from your phone",
    qrMock: "Sample QR (mock)",
    searching: "Looking for controllers…",
    simulateConnect: "Simulate connection",
    cancel: "Cancel",
    quit: "Power off",
    quitQuestion: "Power off Toxinator 3?",
    quitBody: "The session closes and you return to the system. In the prototype, the console would turn off.",
    powerOff: "Power off",
    offTitle: "Toxinator 3 would turn off",
    offBody: "Enter or Esc to return to the prototype.",
    errorTitle: "Can't launch",
    errorDemo: "Capability error",
    errorBody:
      "Maldito Pino needs motion and buttons. Controller 3 (Gamepad) has no motion.",
    reassign: "Reassign controller",
    emptyTitle: "Empty library",
    emptyBody:
      "No games installed. In the real console, games discovered by manifest/entry point would show up here.",
    emptyBack: "Back",
    helpTitle: "Launcher prototype",
    helpIntro:
      "Three UI variants to react to. This is not the final launcher: implementation will be Panda3D/DirectGUI.",
    language: "Language",
    languageDesc: "Changes the console strings.",
    spanish: "Español",
    english: "English",
    master: "Master volume",
    music: "Music",
    sfx: "Effects",
    quality: "Graphics quality",
    textScale: "Text scale",
    controllers: "Controllers",
    controllersDesc: "Assign, connect or release controllers.",
    manageControllers: "Manage",
    connected: "Connected",
    disconnected: "Disconnected",
    emptySlot: "Empty slot",
    assign: "Change controller",
    battery: "Battery",
    noBattery: "No battery",
    warningCaps: "Missing the game's required capabilities",
    gamepad: "Gamepad",
    phone: "Android phone",
    wiimote: "Wiimote",
    currentState: "Current state",
    prototypeNote: "Prototype bar: switch variants without leaving the state.",
    playerSlot: "Player",
    change: "Change",
    closeHelp: "Close help",
    mode: "Mode",
    noModes: "No modes",
    joinHelp: "J: simulate join · C: connect phone · Enter: change controller",
    settingsHelp: "↑↓: row · ←→: value · Enter: manage controllers · Esc: back",
    playersHelp: "←→: slot · Enter: change controller · J: join · C: phone · Esc: back",
    backHome: "Back home",
    launching: "Launching",
    launchReady: "Ready. The game would have opened.",
    backToLauncher: "Back to launcher",
    titleFull: "Full title",
    variantHint: "V cycles variants · H help",
  },
};

const CAP_LABELS = {
  es: {
    motion: "Movimiento",
    buttons: "Botones",
    touch: "Touch",
    axes: "Ejes",
    gyro: "Gyro",
    pointer: "Pointer",
    haptics: "Vibración",
    screen: "Pantalla",
    battery: "Batería",
  },
  en: {
    motion: "Motion",
    buttons: "Buttons",
    touch: "Touch",
    axes: "Axes",
    gyro: "Gyro",
    pointer: "Pointer",
    haptics: "Haptics",
    screen: "Screen",
    battery: "Battery",
  },
};

/* ------------------------------------------------------------------ */
/* State                                                               */
/* ------------------------------------------------------------------ */

const query = new URLSearchParams(location.search);
const requestedVariant = (query.get("variant") || "C").toUpperCase();
const requestedTheme = (query.get("theme") || "feria").toLowerCase();
const KNOWN_SCREENS = [
  "home",
  "detail",
  "settings",
  "players",
  "connecting",
  "error",
  "quit",
  "off",
  "launching",
  "help",
];
const requestedScreen = query.get("screen");
const screenFromQuery =
  requestedScreen === "empty" ? "home" : requestedScreen;

const state = {
  variant: VARIANTS.includes(requestedVariant) ? requestedVariant : "C",
  theme: THEMES.includes(requestedTheme) ? requestedTheme : "feria",
  screen: KNOWN_SCREENS.includes(screenFromQuery) ? screenFromQuery : "home",
  language: "es",
  selectedGame: 0,
  selectedMode: 0,
  selectedSlot: 0,
  selectedSetting: 0,
  helpReturn: "home",
  emptyLibrary: requestedScreen === "empty",
  launchReady: query.get("ready") === "1",
  controllers: DEFAULT_CONTROLLERS.map((controller) => ({
    ...controller,
    caps: [...controller.caps],
  })),
  settings: {
    master: 80,
    music: 55,
    sfx: 80,
    quality: 2,
    textScale: 100,
  },
  gamepadDetected: false,
};

let launchToken = 0;

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function t(key) {
  return I18N[state.language][key] ?? key;
}

function localized(value) {
  if (value && typeof value === "object") {
    return value[state.language] ?? value.es ?? "";
  }
  return value ?? "";
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => {
    switch (character) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#39;";
      default:
        return character;
    }
  });
}

function capLabel(capability) {
  return CAP_LABELS[state.language][capability] ?? capability;
}

function currentGame() {
  return GAMES[state.selectedGame] ?? GAMES[0];
}

function currentMode() {
  const game = currentGame();
  return game.modes[state.selectedMode] ?? game.modes[0];
}

function controllerTypeLabel(type) {
  if (type === "android") return t("phone");
  if (type === "wiimote") return t("wiimote");
  if (type === "gamepad") return t("gamepad");
  return t("emptySlot");
}

function controllerStatus(controller) {
  if (!controller.connected) {
    if (controller.note) return localized(controller.note);
    return t("disconnected");
  }
  if (controller.battery) {
    return `${t("connected")} · ${controller.battery}%`;
  }
  return t("connected");
}

function controllerDisplayName(controller) {
  if (!controller.type) return t("emptySlot");
  return controller.name || controllerTypeLabel(controller.type);
}

function hasAllCaps(controller, required) {
  return required.every((capability) => controller.caps.includes(capability));
}

function hasRequiredController(game = currentGame()) {
  if (!game) return false;
  return state.controllers.some(
    (controller) => controller.connected && hasAllCaps(controller, game.requires)
  );
}

function missingCaps(controller, game = currentGame()) {
  if (!controller.connected || !game) return [];
  return game.requires.filter((capability) => !controller.caps.includes(capability));
}

function connectedCount() {
  return state.controllers.filter((controller) => controller.connected).length;
}

function scrollToTop() {
  const panel = document.querySelector(".panel");
  if (panel) panel.scrollTop = 0;
}

/* ------------------------------------------------------------------ */
/* Icons                                                               */
/* ------------------------------------------------------------------ */

function icon(name, size = 24) {
  const attrs = `viewBox="0 0 64 64" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"`;
  switch (name) {
    case "pin":
      return `<svg ${attrs}><path d="M32 6c-6.5 0-11 4.8-11 11 0 3.8 1.7 6.2 3.8 9.1 2.5 3.4 3.2 6.4 3.2 10.9v14.5c0 3 1.5 5.5 4 5.5s4-2.5 4-5.5V37c0-4.5.7-7.5 3.2-10.9 2.1-2.9 3.8-5.3 3.8-9.1 0-6.2-4.5-11-11-11Z"/><circle cx="28" cy="16" r="1.2" fill="currentColor"/><circle cx="36" cy="16" r="1.2" fill="currentColor"/><path d="M27 23c2 1.6 8 1.6 10 0"/></svg>`;
    case "pin-barker":
      return `<svg ${attrs}><path d="M24 6h16v6H24z"/><path d="M19 12h26"/><path d="M32 14c-5.4 0-9 4-9 8.8 0 3 1.4 5 3.2 7.3 1.8 2.4 2.3 4.2 2.3 7.7v11.5c0 2.4 1.3 4.2 3.5 4.2s3.5-1.8 3.5-4.2V37.8c0-3.5.5-5.3 2.3-7.7 1.8-2.3 3.2-4.3 3.2-7.3 0-4.8-3.6-8.8-9-8.8Z"/><circle cx="28.5" cy="23" r="1.2" fill="currentColor"/><circle cx="35.5" cy="23" r="1.2" fill="currentColor"/><path d="M29 30c1.8 1.3 4.2 1.3 6 0"/><path d="M26 45l-6 3 6 3 6-3Z"/><path d="M38 45l6 3-6 3-6-3Z"/><circle cx="32" cy="48" r="1.5" fill="currentColor"/></svg>`;
    case "ticket-pin":
      return `<svg ${attrs}><path d="M8 14h48v9a7 7 0 0 0 0 14v9H8v-9a7 7 0 0 0 0-14v-9Z"/><path d="M18 20v22" stroke-dasharray="2 3"/><path d="M32 22c-4 0-6.5 2.8-6.5 6.2 0 2.2 1 3.5 2.2 5 1.4 1.8 1.8 3.2 1.8 5.8v7c0 1.6.9 2.8 2.5 2.8s2.5-1.2 2.5-2.8v-7c0-2.6.4-4 1.8-5.8 1.2-1.5 2.2-2.8 2.2-5C38.5 24.8 36 22 32 22Z"/><circle cx="29.5" cy="28" r="1" fill="currentColor"/><circle cx="34.5" cy="28" r="1" fill="currentColor"/></svg>`;
    case "kart":
      return `<svg ${attrs}><circle cx="32" cy="32" r="19"/><circle cx="32" cy="32" r="6"/><path d="M32 26V13M27 34 15 41M37 34l12 7"/><path d="M20 18c8 2 16 2 24 0"/></svg>`;
    case "tennis":
      return `<svg ${attrs}><ellipse cx="26" cy="24" rx="12" ry="16" transform="rotate(-24 26 24)"/><path d="M34 36 50 53"/><circle cx="51" cy="17" r="4"/></svg>`;
    case "phone":
      return `<svg ${attrs}><rect x="20" y="8" width="24" height="48" rx="6"/><path d="M29 50h6"/></svg>`;
    case "wiimote":
      return `<svg ${attrs}><rect x="24" y="8" width="16" height="48" rx="8"/><circle cx="32" cy="18" r="3"/><path d="M27 29h10M32 24v10"/></svg>`;
    case "gamepad":
      return `<svg ${attrs}><path d="M19 24h26c6 0 10 5 10 12s-4 12-9 12c-4 0-6-3-10-3H28c-4 0-6 3-10 3-5 0-9-5-9-12s4-12 10-12Z"/><path d="M23 32v8M19 36h8"/><circle cx="43" cy="32" r="2"/><circle cx="49" cy="37" r="2"/></svg>`;
    case "empty":
      return `<svg ${attrs} stroke-dasharray="4 5"><circle cx="32" cy="32" r="19"/><path d="M32 24v16M24 32h16"/></svg>`;
    case "settings":
      return `<svg ${attrs}><circle cx="32" cy="32" r="8"/><path d="M32 7v7M32 50v7M7 32h7M50 32h7M14.4 14.4l5 5M44.6 44.6l5 5M49.6 14.4l-5 5M19.4 44.6l-5 5"/></svg>`;
    case "players":
      return `<svg ${attrs}><circle cx="24" cy="24" r="8"/><circle cx="45" cy="26" r="6"/><path d="M9 51c2-9 7-13 15-13s13 4 15 13M37 39c8-1 14 3 16 12"/></svg>`;
    case "globe":
      return `<svg ${attrs}><circle cx="32" cy="32" r="20"/><path d="M12 32h40M32 12c6 6 9 12 9 20s-3 14-9 20c-6-6-9-12-9-20s3-14 9-20Z"/></svg>`;
    case "power":
      return `<svg ${attrs}><path d="M32 9v19"/><path d="M20 18a18 18 0 1 0 24 0"/></svg>`;
    case "warning":
      return `<svg ${attrs}><path d="M32 8 58 54H6L32 8Z"/><path d="M32 24v14"/><circle cx="32" cy="45" r="1.5" fill="currentColor"/></svg>`;
    case "play":
      return `<svg ${attrs}><path d="M24 17v30l26-15L24 17Z" fill="currentColor" stroke="none"/></svg>`;
    case "check":
      return `<svg ${attrs}><path d="m14 33 12 12 24-27"/></svg>`;
    case "plus":
      return `<svg ${attrs}><path d="M32 14v36M14 32h36"/></svg>`;
    case "chevron-left":
      return `<svg ${attrs}><path d="M39 17 24 32l15 15"/></svg>`;
    case "chevron-right":
      return `<svg ${attrs}><path d="m25 17 15 15-15 15"/></svg>`;
    default:
      return "";
  }
}

function controllerIcon(controller, size = 22) {
  if (!controller || !controller.connected) return icon("empty", size);
  if (controller.type === "android") return icon("phone", size);
  if (controller.type === "wiimote") return icon("wiimote", size);
  if (controller.type === "gamepad") return icon("gamepad", size);
  return icon("empty", size);
}

function gameIconName(game) {
  return state.theme === "feria" && game.id === "maldito-pino" ? "pin-barker" : game.icon;
}

function brandMarkIcon(size) {
  return icon(state.theme === "feria" ? "ticket-pin" : "pin", size);
}

function gameArt(game, extra = "") {
  return `<div class="game-art ${extra}" style="--game-accent:${game.accent}">${icon(gameIconName(game), 96)}</div>`;
}

/* ------------------------------------------------------------------ */
/* Home variants                                                       */
/* ------------------------------------------------------------------ */

function renderTopbar() {
  return `<header class="topbar">
    <div class="brand"><span class="mark">${brandMarkIcon(28)}</span>Toxinator <small>3</small><span class="brand-tag">${THEME_TAGLINES[state.theme]}</span></div>
    <div class="topbar-center">${t("home")}</div>
    <div class="topbar-actions">
      <button class="pill-button" data-action="language"><span class="dot"></span>${state.language.toUpperCase()}</button>
      <button class="pill-button" data-action="players">${icon("players", 18)}<span class="label">${t("players")}</span><span class="badge accent">${connectedCount()}/4</span></button>
      <button class="pill-button icon-only" data-action="settings" aria-label="${t("settings")}">${icon("settings", 18)}</button>
    </div>
  </header>`;
}

function renderTopC() {
  const dots = state.controllers
    .map((controller) => {
      if (!controller.connected) return `<span class="status-dot" title="${t("emptySlot")}"></span>`;
      const missing = missingCaps(controller);
      return `<span class="status-dot ${missing.length ? "warn" : "online"}" title="${escapeHtml(controller.name || controllerTypeLabel(controller.type))}"></span>`;
    })
    .join("");

  return `<header class="top-c">
    <div class="brand"><span class="mark">${brandMarkIcon(26)}</span>Toxinator <small>3</small><span class="brand-tag">${THEME_TAGLINES[state.theme]}</span></div>
    <div class="topbar-actions">
      <div class="status-dots">${dots}<span class="badge">${connectedCount()}/4</span></div>
      <button class="pill-button" data-action="language"><span class="dot"></span>${state.language.toUpperCase()}</button>
      <button class="pill-button icon-only" data-action="players" aria-label="${t("players")}">${icon("players", 18)}</button>
      <button class="pill-button icon-only" data-action="settings" aria-label="${t("settings")}">${icon("settings", 18)}</button>
    </div>
  </header>`;
}

function renderControllerChip(controller) {
  const missing = missingCaps(controller);
  const classes = [
    "controller-chip",
    controller.connected ? "online" : "offline",
    missing.length ? "warn" : "",
    controller.slot === state.selectedSlot ? "selected" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const status = `${controllerTypeLabel(controller.type)} · ${controllerStatus(controller)}`;

  return `<button class="${classes}" data-action="players" data-slot="${controller.slot}">
    <span class="icon">${controllerIcon(controller)}</span>
    <span class="meta">
      <span class="name">P${controller.slot} · ${escapeHtml(controllerDisplayName(controller))}</span>
      <span class="sub">${escapeHtml(status)}</span>
    </span>
    <span class="state-dot"></span>
  </button>`;
}

function renderControllerStrip() {
  return `<div class="controller-strip">${state.controllers.map(renderControllerChip).join("")}</div>`;
}

function renderHints() {
  const hints = [
    ["←↑→↓", t("navigate")],
    ["Enter", t("select")],
    ["Esc", t("back")],
    ["P", t("players")],
    ["S", t("settings")],
    ["H", t("help")],
    ["V", t("variant")],
    ["T", t("theme")],
  ];
  return `<div class="hints">${hints
    .map(([key, label]) => `<span><kbd>${key}</kbd>${label}</span>`)
    .join("")}</div>`;
}

function renderGameCard(game, index) {
  const selected = index === state.selectedGame;
  return `<button class="game-card ${selected ? "selected" : ""}" data-action="open-detail" data-game="${index}" style="--game-accent:${game.accent}">
    ${gameArt(game)}
    <div class="card-title">${escapeHtml(game.title)}</div>
    <div class="card-sub">${escapeHtml(game.subtitle)}</div>
    <div class="card-meta">
      <span class="badge ${game.installed ? "accent" : ""}">${game.installed ? t("installed") : t("notInstalled")}</span>
      <span class="badge">${game.players[0]}–${game.players[1]} ${t("playersShort")}</span>
    </div>
  </button>`;
}

function renderModePills(game) {
  return `<div class="mode-pills">${game.modes
    .map(
      (mode, index) =>
        `<button class="mode-pill ${index === state.selectedMode ? "selected" : ""}" data-action="mode" data-mode="${index}">${escapeHtml(localized(mode.name))}</button>`
    )
    .join("")}</div>`;
}

function renderDetailsA() {
  const game = currentGame();
  const mode = currentMode();
  return `<div class="details-a" style="--game-accent:${game.accent}">
    <div>
      <h2>${escapeHtml(game.title)} <span class="muted" style="font-size:0.55em;font-weight:500">${escapeHtml(game.subtitle)}</span></h2>
      <p>${escapeHtml(localized(game.description))}</p>
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:12px">
        ${renderModePills(game)}
        <span class="badge">${escapeHtml(localized(mode.desc))}</span>
      </div>
    </div>
    <div class="details-actions">
      <button class="secondary-button" data-action="open-detail">${t("modes")}</button>
      <button class="primary-button" data-action="launch" ${game.installed ? "" : "disabled"}>${icon("play", 18)}${t("play")}</button>
    </div>
  </div>`;
}

function renderHomeA() {
  return `<div class="launcher home-a">
    ${renderTopbar()}
    <div class="carousel-wrap"><div class="carousel">${GAMES.map(renderGameCard).join("")}</div></div>
    ${renderDetailsA()}
    ${renderControllerStrip()}
    ${renderHints()}
  </div>`;
}

function renderSideItem(game, index) {
  return `<button class="side-item ${index === state.selectedGame ? "selected" : ""} ${game.installed ? "installed" : ""}" data-action="open-detail" data-game="${index}" style="--game-accent:${game.accent}">
    ${gameArt(game)}
    <span><span class="title">${escapeHtml(game.title)}</span><span class="sub">${escapeHtml(game.subtitle)}</span></span>
    <span class="state"></span>
  </button>`;
}

function renderHomeB() {
  const game = currentGame();
  const mode = currentMode();
  return `<div class="launcher home-b">
    ${renderTopbar()}
    <aside class="sidebar-b">
      <div class="sidebar-title">${t("library")}</div>
      ${GAMES.map(renderSideItem).join("")}
    </aside>
    <section class="hero-b" style="--game-accent:${game.accent}">
      <div class="hero-art-b">
        ${gameArt(game)}
        <div class="hero-overlay-b">
          <h2>${escapeHtml(game.title)}</h2>
          <p>${escapeHtml(localized(game.description))}</p>
        </div>
      </div>
      <div class="hero-actions-b">
        <div class="hero-meta-b">
          <span class="badge accent">${game.installed ? t("installed") : t("notInstalled")}</span>
          <span class="badge">${game.players[0]}–${game.players[1]} ${t("playersShort")}</span>
          <span class="badge">${escapeHtml(localized(mode.name))}</span>
        </div>
        <div class="details-actions">
          <button class="secondary-button" data-action="players">${icon("players", 18)}${t("players")}</button>
          <button class="primary-button" data-action="open-detail" ${game.installed ? "" : "disabled"}>${t("play")}</button>
        </div>
      </div>
    </section>
    <aside class="controller-panel-b">
      <div class="panel-heading"><span>${t("controllers")}</span><button data-action="players">${t("manageControllers")}</button></div>
      ${renderControllerStrip()}
      <button class="secondary-button" data-action="connect" style="margin-top:2px">${icon("phone", 16)}${t("connectPhone")}</button>
    </aside>
    ${renderHints()}
  </div>`;
}

function renderTile(game, index) {
  return `<button class="tile ${index === state.selectedGame ? "selected" : ""}" data-action="open-detail" data-game="${index}" style="--game-accent:${game.accent}">
    ${gameArt(game)}
    <div class="tile-label">
      <div class="title">${escapeHtml(game.title)}</div>
      <div class="sub">${game.installed ? escapeHtml(game.subtitle) : t("comingSoon")}</div>
    </div>
  </button>`;
}

function renderHomeC() {
  const game = currentGame();
  const mode = currentMode();
  return `<div class="launcher home-c">
    ${renderTopC()}
    <div class="grid-c">
      ${GAMES.map(renderTile).join("")}
      <button class="tile empty-tile" data-action="empty" style="--game-accent:#8b9bb6">
        ${gameArt({ accent: "#8b9bb6", icon: "plus" })}
        <div class="tile-label"><div class="title">${t("library")}</div><div class="sub">${t("comingSoon")}</div></div>
      </button>
    </div>
    <div class="sheet-c" style="--game-accent:${game.accent}">
      <div>
        <h2>${escapeHtml(game.title)} <span class="muted" style="font-size:0.55em;font-weight:500">${escapeHtml(game.subtitle)}</span></h2>
        <p>${escapeHtml(localized(mode.desc))}</p>
      </div>
      <div class="sheet-actions-c">
        ${renderModePills(game)}
        <button class="primary-button" data-action="open-detail" ${game.installed ? "" : "disabled"}>${t("play")}</button>
      </div>
    </div>
    ${renderHints()}
  </div>`;
}

function renderEmptyHome() {
  return `<div class="launcher">
    ${renderTopbar()}
    <div class="empty-home">
      ${icon("plus", 54)}
      <h2>${t("emptyTitle")}</h2>
      <p>${t("emptyBody")}</p>
      <button class="secondary-button" data-action="empty">${t("emptyBack")}</button>
    </div>
    ${renderHints()}
  </div>`;
}

function renderHome() {
  if (state.emptyLibrary) return renderEmptyHome();
  if (state.variant === "B") return renderHomeB();
  if (state.variant === "C") return renderHomeC();
  return renderHomeA();
}

/* ------------------------------------------------------------------ */
/* Overlays                                                            */
/* ------------------------------------------------------------------ */

function renderDetailOverlay() {
  const game = currentGame();
  const mode = currentMode();
  return `<div class="overlay">
    <section class="panel" style="--game-accent:${game.accent}">
      <div class="panel-header">
        <div>
          <h2>${t("gameDetails")}</h2>
          <p>${game.installed ? t("ready") : t("comingSoon")}</p>
        </div>
        <button class="panel-close" data-action="back" aria-label="${t("close")}">×</button>
      </div>
      <div class="panel-body">
        <div class="detail-layout">
          <div class="detail-art game-art" style="--game-accent:${game.accent}">${icon(gameIconName(game), 120)}</div>
          <div class="detail-info">
            <h3>${escapeHtml(game.title)}</h3>
            <p class="subtitle">${escapeHtml(game.subtitle)}</p>
            <p class="description">${escapeHtml(localized(game.description))}</p>
            <div class="mode-list">
              ${game.modes
                .map(
                  (item, index) => `<button class="mode-row ${index === state.selectedMode ? "selected" : ""}" data-action="mode" data-mode="${index}">
                    <span><span class="mode-name">${escapeHtml(localized(item.name))}</span><span class="mode-desc">${escapeHtml(localized(item.desc))}</span></span>
                    ${index === state.selectedMode ? icon("check", 20) : ""}
                  </button>`
                )
                .join("")}
            </div>
            <div class="meta-grid">
              <div class="meta-item"><div class="label">${t("players")}</div><div class="value">${game.players[0]}–${game.players[1]}</div></div>
              <div class="meta-item"><div class="label">${t("version")}</div><div class="value">${escapeHtml(game.version)}</div></div>
              <div class="meta-item"><div class="label">${t("requiredCaps")}</div><div class="value">${game.requires.map(capLabel).join(" · ")}</div></div>
              <div class="meta-item"><div class="label">${t("mode")}</div><div class="value">${escapeHtml(localized(mode.name))}</div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="panel-actions">
        <button class="secondary-button" data-action="back">${t("back")}</button>
        <button class="primary-button" data-action="launch" ${game.installed ? "" : "disabled"}>${icon("play", 18)}${t("play")}</button>
      </div>
    </section>
  </div>`;
}

function settingValue(key) {
  switch (key) {
    case "language":
      return state.language === "es" ? t("spanish") : t("english");
    case "master":
      return `${state.settings.master}%`;
    case "music":
      return `${state.settings.music}%`;
    case "sfx":
      return `${state.settings.sfx}%`;
    case "quality":
      return QUALITY_LEVELS[state.language][state.settings.quality];
    case "textScale":
      return `${state.settings.textScale}%`;
    case "controllers":
      return t("manageControllers");
    default:
      return "";
  }
}

function settingLabel(key) {
  if (key === "controllers") return t("controllers");
  return t(key);
}

function settingDescription(key) {
  if (key === "controllers") return t("controllersDesc");
  if (key === "language") return t("languageDesc");
  return "";
}

function renderSettingsOverlay() {
  return `<div class="overlay">
    <section class="panel">
      <div class="panel-header">
        <div><h2>${t("settings")}</h2><p>${t("settingsHelp")}</p></div>
        <button class="panel-close" data-action="back" aria-label="${t("close")}">×</button>
      </div>
      <div class="panel-body">
        <div class="settings-list">
          ${SETTING_KEYS.map(
            (key, index) => `<div class="setting-row ${index === state.selectedSetting ? "selected" : ""}" data-action="setting" data-index="${index}" role="button" tabindex="0">
              <div>
                <div class="setting-label">${settingLabel(key)}</div>
                ${settingDescription(key) ? `<div class="setting-desc">${settingDescription(key)}</div>` : ""}
              </div>
              <div class="setting-value">
                <button class="value-step" data-action="setting-dec" data-index="${index}" aria-label="−">‹</button>
                <span>${escapeHtml(settingValue(key))}</span>
                <button class="value-step" data-action="setting-inc" data-index="${index}" aria-label="+">›</button>
              </div>
            </div>`
          ).join("")}
        </div>
      </div>
      <div class="panel-actions"><button class="secondary-button" data-action="back">${t("back")}</button></div>
    </section>
  </div>`;
}

function renderSlot(controller, index) {
  const missing = missingCaps(controller);
  const selected = index === state.selectedSlot;
  return `<div class="slot-card ${selected ? "selected" : ""}" data-action="slot" data-slot="${index}" role="button" tabindex="0">
    <div class="slot-head">
      <span class="slot-title">${t("player")} ${index + 1}</span>
      <span class="slot-status"><span class="status-dot ${controller.connected ? (missing.length ? "warn" : "online") : ""}"></span>${escapeHtml(controllerStatus(controller))}</span>
    </div>
    <div class="slot-body">
      <span class="slot-icon ${controller.connected ? "" : "offline"}">${controllerIcon(controller, 24)}</span>
      <div>
        <div class="slot-name">${escapeHtml(controllerDisplayName(controller))}</div>
        <div class="slot-caps">${controller.caps.map((capability) => `<span class="badge">${capLabel(capability)}</span>`).join("")}</div>
      </div>
    </div>
    ${missing.length ? `<div class="slot-warning">${icon("warning", 15)}${t("warningCaps")}: ${missing.map(capLabel).join(", ")}</div>` : ""}
    <div><button class="secondary-button" data-action="slot-cycle" data-slot="${index}">${t("assign")}</button></div>
  </div>`;
}

function renderPlayersOverlay() {
  const game = currentGame();
  return `<div class="overlay">
    <section class="panel">
      <div class="panel-header">
        <div><h2>${t("players")}</h2><p>${t("playersHelp")}</p></div>
        <button class="panel-close" data-action="back" aria-label="${t("close")}">×</button>
      </div>
      <div class="panel-body">
        <div class="players-summary">
          <div>
            <div class="cap-label" style="color:var(--muted);font-size:0.68rem;letter-spacing:0.12em;text-transform:uppercase">${t("requiredCaps")}</div>
            <div class="caps">${game.requires.map((capability) => `<span class="badge accent">${capLabel(capability)}</span>`).join("")}</div>
          </div>
          <span class="badge ${hasRequiredController(game) ? "accent" : "warn"}">${hasRequiredController(game) ? t("ready") : t("noController")}</span>
        </div>
        <div class="slots-grid">${state.controllers.map(renderSlot).join("")}</div>
      </div>
      <div class="panel-actions">
        <button class="secondary-button" data-action="connect">${icon("phone", 16)}${t("connectPhone")}</button>
        <button class="secondary-button" data-action="join">${t("simulateJoin")}</button>
        <button class="primary-button" data-action="back">${t("done")}</button>
      </div>
    </section>
  </div>`;
}

function renderQr() {
  let seed = 47;
  const cells = [];
  for (let y = 0; y < 11; y += 1) {
    for (let x = 0; x < 11; x += 1) {
      const finder =
        (x < 3 && y < 3) || (x > 7 && y < 3) || (x < 3 && y > 7);
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      const finderOn =
        (x === 0 || x === 2 || y === 0 || y === 2) || (x === 1 && y === 1);
      const on = finder ? finderOn : ((seed >> 8) & 1) === 1;
      cells.push(`<span class="${on ? "" : "blank"}"></span>`);
    }
  }
  return `<div class="qr" aria-hidden="true">${cells.join("")}</div>`;
}

function renderConnectingOverlay() {
  return `<div class="overlay">
    <section class="panel">
      <div class="panel-header">
        <div><h2>${t("connecting")}</h2><p>${t("scanQr")}</p></div>
        <button class="panel-close" data-action="back" aria-label="${t("close")}">×</button>
      </div>
      <div class="panel-body">
        <div class="qr-wrap">
          ${renderQr()}
          <div class="connecting-copy">
            <div class="inline-status"><span class="spinner"></span>${t("searching")}</div>
            <p>${t("qrMock")}. En la consola final el QR va a llevar la URL HTTPS con room y token.</p>
            <div class="meta-grid">
              <div class="meta-item"><div class="label">${t("phone")}</div><div class="value">${t("connected")}</div></div>
              <div class="meta-item"><div class="label">${t("players")}</div><div class="value">${connectedCount()}/4</div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="panel-actions">
        <button class="secondary-button" data-action="back">${t("cancel")}</button>
        <button class="primary-button" data-action="connect-phone">${icon("check", 18)}${t("simulateConnect")}</button>
      </div>
    </section>
  </div>`;
}

function renderErrorOverlay() {
  return `<div class="overlay">
    <section class="panel error-panel">
      <div class="panel-header">
        <div>
          <div class="error-icon">${icon("warning", 24)}</div>
          <h2>${t("errorTitle")}</h2>
          <p>${t("errorBody")}</p>
        </div>
        <button class="panel-close" data-action="back" aria-label="${t("close")}">×</button>
      </div>
      <div class="panel-body">
        <div class="meta-grid">
          <div class="meta-item"><div class="label">${t("requiredCaps")}</div><div class="value">${currentGame().requires.map(capLabel).join(" · ")}</div></div>
          <div class="meta-item"><div class="label">${t("controllers")}</div><div class="value">${connectedCount()}/4</div></div>
        </div>
      </div>
      <div class="panel-actions">
        <button class="secondary-button" data-action="back">${t("back")}</button>
        <button class="primary-button" data-action="reassign">${t("reassign")}</button>
      </div>
    </section>
  </div>`;
}

function renderQuitOverlay() {
  return `<div class="overlay">
    <section class="panel">
      <div class="panel-header">
        <div><h2>${t("quitQuestion")}</h2><p>${t("quitBody")}</p></div>
        <button class="panel-close" data-action="back" aria-label="${t("close")}">×</button>
      </div>
      <div class="panel-actions">
        <button class="secondary-button" data-action="back">${t("cancel")}</button>
        <button class="primary-button" data-action="power-off">${icon("power", 18)}${t("powerOff")}</button>
      </div>
    </section>
  </div>`;
}

function renderOffOverlay() {
  return `<div class="overlay">
    <div class="off-screen">
      <div class="brand" style="justify-content:center"><span class="mark">${brandMarkIcon(30)}</span>Toxinator <small>3</small><span class="brand-tag">${THEME_TAGLINES[state.theme]}</span></div>
      <h2>${t("offTitle")}</h2>
      <p>${t("offBody")}</p>
      <div><button class="secondary-button" data-action="back">${t("back")}</button></div>
    </div>
  </div>`;
}

function renderLaunchOverlay() {
  const game = currentGame();
  const mode = currentMode();
  return `<div class="overlay">
    <div class="launch-panel" style="--game-accent:${game.accent}">
      <div class="launch-art game-art">${icon(gameIconName(game), 86)}</div>
      <h2>${escapeHtml(game.title)}</h2>
      <p>${escapeHtml(localized(mode.name))} · ${game.players[0]}–${game.players[1]} ${t("playersShort")}</p>
      <div class="progress"><span style="width:${state.launchReady ? "100%" : "0%"};${state.launchReady ? "animation:none" : ""}"></span></div>
      <div class="launch-status">${state.launchReady ? t("launchReady") : `${t("launching")}…`}</div>
      ${state.launchReady ? `<div style="margin-top:22px"><button class="primary-button" data-action="back">${t("backToLauncher")}</button></div>` : `<p class="muted" style="margin-top:18px">Esc ${t("cancel").toLowerCase()}</p>`}
    </div>
  </div>`;
}

function renderHelpOverlay() {
  const rows = [
    ["← ↑ → ↓", t("navigate")],
    ["Enter / A", t("select")],
    ["Esc / B", t("back")],
    ["S / Start", t("settings")],
    ["P", t("players")],
    ["C", t("connectPhone")],
    ["E", t("errorDemo")],
    ["0", t("emptyTitle")],
    ["Q", t("quit")],
    ["L", t("language")],
    ["H", t("help")],
    ["V", t("variant")],
    ["T", t("theme")],
    ["J", t("simulateJoin")],
  ];
  return `<div class="overlay">
    <section class="panel">
      <div class="panel-header">
        <div><h2>${t("helpTitle")}</h2><p>${t("helpIntro")}</p></div>
        <button class="panel-close" data-action="back" aria-label="${t("closeHelp")}">×</button>
      </div>
      <div class="panel-body">
        <div class="help-grid">${rows.map(([key, label]) => `<div class="help-row"><code>${key}</code><span>${label}</span></div>`).join("")}</div>
        <div class="state-line">
          <strong>${t("currentState")}:</strong> variant <code>${state.variant}</code> · screen <code>${state.screen}</code> · lang <code>${state.language}</code> · game <code>${escapeHtml(currentGame().title)}</code> · mode <code>${escapeHtml(localized(currentMode().name))}</code> · controllers <code>${connectedCount()}/4</code>
        </div>
        <p class="muted" style="margin:14px 0 0">${t("prototypeNote")}</p>
      </div>
      <div class="panel-actions"><button class="primary-button" data-action="back">${t("done")}</button></div>
    </section>
  </div>`;
}

function renderOverlay() {
  switch (state.screen) {
    case "detail":
      return renderDetailOverlay();
    case "settings":
      return renderSettingsOverlay();
    case "players":
      return renderPlayersOverlay();
    case "connecting":
      return renderConnectingOverlay();
    case "error":
      return renderErrorOverlay();
    case "quit":
      return renderQuitOverlay();
    case "off":
      return renderOffOverlay();
    case "launching":
      return renderLaunchOverlay();
    case "help":
      return renderHelpOverlay();
    default:
      return "";
  }
}

/* ------------------------------------------------------------------ */
/* Render                                                              */
/* ------------------------------------------------------------------ */

function render() {
  const app = document.getElementById("app");
  document.body.className = `theme-${state.theme}`;
  app.className = `variant-${state.variant.toLowerCase()}`;
  app.innerHTML = `${renderHome()}${renderOverlay()}`;
  renderProtoBar();
}

function renderProtoBar() {
  const bar = document.getElementById("proto-bar");
  if (!bar) return;
  const compact = window.matchMedia("(max-width: 700px)").matches;
  bar.innerHTML = `<span class="proto-label">Prototipo</span>
    <button class="arrow" data-action="cycle-variant" data-delta="-1" aria-label="Variante anterior">‹</button>
    ${VARIANTS.map((variant) => `<button class="variant-button ${state.variant === variant ? "active" : ""}" data-action="variant" data-variant="${variant}">${compact ? variant : `${variant} · ${VARIANT_NAMES[variant]}`}</button>`).join("")}
    <span class="divider"></span>
    <span class="proto-label">Tema</span>
    ${THEMES.map((theme) => `<button class="variant-button ${state.theme === theme ? "active" : ""}" data-action="theme" data-theme="${theme}">${compact ? THEME_NAMES[theme].replace(" 78", "") : THEME_NAMES[theme]}</button>`).join("")}
    <span class="divider"></span>
    <button class="arrow" data-action="help" aria-label="${t("help")}">?</button>
    <button class="arrow" data-action="cycle-variant" data-delta="1" aria-label="Variante siguiente">›</button>`;
}

/* ------------------------------------------------------------------ */
/* Actions                                                             */
/* ------------------------------------------------------------------ */

function updateUrl() {
  try {
    const url = new URL(location.href);
    url.searchParams.set("variant", state.variant);
    url.searchParams.set("theme", state.theme);
    history.replaceState(null, "", url);
  } catch {
    // file:// and some embedded contexts may reject history updates.
  }
}

function setVariant(variant) {
  if (!VARIANTS.includes(variant)) return;
  state.variant = variant;
  updateUrl();
  render();
}

function setTheme(theme) {
  if (!THEMES.includes(theme)) return;
  state.theme = theme;
  updateUrl();
  render();
}

function cycleTheme(delta) {
  const index = THEMES.indexOf(state.theme);
  const next = (index + delta + THEMES.length) % THEMES.length;
  setTheme(THEMES[next]);
}

function cycleVariant(delta) {
  const index = VARIANTS.indexOf(state.variant);
  const next = (index + delta + VARIANTS.length) % VARIANTS.length;
  setVariant(VARIANTS[next]);
}

function toggleLanguage() {
  state.language = state.language === "es" ? "en" : "es";
  render();
}

function openDetail(gameIndex) {
  if (Number.isInteger(gameIndex) && GAMES[gameIndex]) {
    state.selectedGame = gameIndex;
    state.selectedMode = 0;
  }
  state.screen = "detail";
  render();
}

function openSettings() {
  state.screen = "settings";
  state.selectedSetting = 0;
  render();
}

function openPlayers() {
  state.screen = "players";
  render();
}

function openConnecting() {
  state.screen = "connecting";
  render();
}

function openError() {
  state.screen = "error";
  render();
}

function openQuit() {
  state.screen = "quit";
  render();
}

function openEmpty() {
  state.emptyLibrary = true;
  state.screen = "home";
  render();
}

function closeEmpty() {
  state.emptyLibrary = false;
  state.screen = "home";
  render();
}

function toggleHelp() {
  if (state.screen === "help") {
    state.screen = state.helpReturn || "home";
  } else {
    state.helpReturn = state.screen;
    state.screen = "help";
  }
  render();
}

function back() {
  if (state.screen === "help") {
    state.screen = state.helpReturn || "home";
  } else if (state.screen === "home") {
    state.screen = "quit";
  } else {
    state.screen = "home";
  }
  render();
}

function launchGame() {
  const game = currentGame();
  if (!game.installed) return;
  state.screen = "launching";
  state.launchReady = false;
  const token = ++launchToken;
  window.setTimeout(() => {
    if (state.screen === "launching" && token === launchToken) {
      state.launchReady = true;
      render();
    }
  }, 2200);
  render();
}

function cycleSlot(index) {
  const controller = state.controllers[index];
  if (!controller) return;
  const order = ["android", "wiimote", "gamepad", null];
  const current = order.indexOf(controller.type);
  const next = order[(current + 1) % order.length];
  state.selectedSlot = index;

  if (next === "android") {
    Object.assign(controller, {
      type: "android",
      name: "Pixel 8",
      connected: true,
      caps: ["motion", "buttons", "touch"],
      battery: 78,
      note: null,
    });
  } else if (next === "wiimote") {
    Object.assign(controller, {
      type: "wiimote",
      name: "Wii Remote",
      connected: true,
      caps: ["motion", "buttons"],
      battery: 40,
      note: null,
    });
  } else if (next === "gamepad") {
    Object.assign(controller, {
      type: "gamepad",
      name: "Gamepad",
      connected: true,
      caps: ["buttons", "axes"],
      battery: null,
      note: null,
    });
  } else {
    Object.assign(controller, {
      type: null,
      name: "",
      connected: false,
      caps: [],
      battery: null,
      note: null,
    });
  }
  render();
}

function simulateJoin() {
  const wiimote = state.controllers.find(
    (controller) => controller.type === "wiimote" && !controller.connected
  );
  if (wiimote) {
    Object.assign(wiimote, {
      connected: true,
      caps: ["motion", "buttons"],
      battery: 40,
      note: null,
    });
  } else {
    const empty = state.controllers.find((controller) => !controller.connected);
    if (empty) {
      Object.assign(empty, {
        type: "android",
        name: "Celular",
        connected: true,
        caps: ["motion", "buttons", "touch"],
        battery: 65,
        note: null,
      });
    }
  }
  render();
}

function connectPhone() {
  const phone = state.controllers[0];
  Object.assign(phone, {
    type: "android",
    name: "Pixel 8",
    connected: true,
    caps: ["motion", "buttons", "touch"],
    battery: 78,
    note: null,
  });
  state.screen = "home";
  render();
}

function changeSetting(index, delta) {
  const key = SETTING_KEYS[index];
  if (!key) return;
  state.selectedSetting = index;
  if (key === "language") {
    toggleLanguage();
    return;
  }
  if (key === "master" || key === "music" || key === "sfx") {
    state.settings[key] = Math.max(0, Math.min(100, state.settings[key] + delta * 10));
  } else if (key === "quality") {
    const count = QUALITY_LEVELS[state.language].length;
    state.settings.quality = Math.max(0, Math.min(count - 1, state.settings.quality + delta));
  } else if (key === "textScale") {
    const current = TEXT_SCALES.indexOf(state.settings.textScale);
    const next = Math.max(0, Math.min(TEXT_SCALES.length - 1, current + delta));
    state.settings.textScale = TEXT_SCALES[next];
  } else if (key === "controllers") {
    if (delta !== 0) openPlayers();
    return;
  }
  render();
}

function activateSetting(index) {
  const key = SETTING_KEYS[index];
  if (key === "controllers") {
    openPlayers();
  } else if (key === "language") {
    toggleLanguage();
  }
}

function navigate(direction) {
  if (state.screen === "home") {
    if (state.emptyLibrary) return;
    const delta = direction === "left" || direction === "up" ? -1 : 1;
    state.selectedGame = (state.selectedGame + delta + GAMES.length) % GAMES.length;
    state.selectedMode = 0;
    render();
    return;
  }

  if (state.screen === "detail") {
    if (direction === "left" || direction === "right") {
      const modes = currentGame().modes.length;
      const delta = direction === "left" ? -1 : 1;
      state.selectedMode = (state.selectedMode + delta + modes) % modes;
      render();
    }
    return;
  }

  if (state.screen === "settings") {
    if (direction === "up" || direction === "down") {
      const delta = direction === "up" ? -1 : 1;
      state.selectedSetting =
        (state.selectedSetting + delta + SETTING_KEYS.length) % SETTING_KEYS.length;
      render();
    } else if (direction === "left" || direction === "right") {
      changeSetting(state.selectedSetting, direction === "left" ? -1 : 1);
    }
    return;
  }

  if (state.screen === "players") {
    if (direction === "left" || direction === "right") {
      const delta = direction === "left" ? -1 : 1;
      state.selectedSlot =
        (state.selectedSlot + delta + state.controllers.length) % state.controllers.length;
      render();
    }
    return;
  }

  if (state.screen === "connecting" || state.screen === "error" || state.screen === "quit" || state.screen === "help") {
    return;
  }
}

function select() {
  switch (state.screen) {
    case "home":
      if (!state.emptyLibrary) openDetail(state.selectedGame);
      break;
    case "detail":
      launchGame();
      break;
    case "settings":
      activateSetting(state.selectedSetting);
      break;
    case "players":
      cycleSlot(state.selectedSlot);
      break;
    case "connecting":
      connectPhone();
      break;
    case "error":
      openPlayers();
      break;
    case "empty":
      closeEmpty();
      break;
    case "quit":
      state.screen = "off";
      render();
      break;
    case "off":
      state.screen = "home";
      render();
      break;
    case "launching":
      if (state.launchReady) {
        state.screen = "home";
        render();
      }
      break;
    case "help":
      toggleHelp();
      break;
    default:
      break;
  }
}

/* ------------------------------------------------------------------ */
/* Input                                                               */
/* ------------------------------------------------------------------ */

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  const overlay = event.target.classList && event.target.classList.contains("overlay");
  if (overlay) {
    back();
    return;
  }
  if (!target) return;

  const action = target.dataset.action;
  switch (action) {
    case "variant":
      setVariant(target.dataset.variant);
      break;
    case "theme":
      setTheme(target.dataset.theme);
      break;
    case "cycle-variant":
      cycleVariant(Number(target.dataset.delta) || 1);
      break;
    case "language":
      toggleLanguage();
      break;
    case "settings":
      openSettings();
      break;
    case "players":
      openPlayers();
      break;
    case "open-detail":
      openDetail(Number(target.dataset.game));
      break;
    case "mode":
      state.selectedMode = Number(target.dataset.mode) || 0;
      render();
      break;
    case "launch":
      launchGame();
      break;
    case "back":
      back();
      break;
    case "setting":
      state.selectedSetting = Number(target.dataset.index) || 0;
      render();
      break;
    case "setting-dec":
      changeSetting(Number(target.dataset.index), -1);
      break;
    case "setting-inc":
      changeSetting(Number(target.dataset.index), 1);
      break;
    case "slot":
      state.selectedSlot = Number(target.dataset.slot) || 0;
      render();
      break;
    case "slot-cycle":
      cycleSlot(Number(target.dataset.slot));
      break;
    case "join":
      simulateJoin();
      break;
    case "connect":
      openConnecting();
      break;
    case "connect-phone":
      connectPhone();
      break;
    case "reassign":
      openPlayers();
      break;
    case "power-off":
      state.screen = "off";
      render();
      break;
    case "empty":
      if (state.emptyLibrary) closeEmpty();
      else openEmpty();
      break;
    case "quit":
      openQuit();
      break;
    case "help":
      toggleHelp();
      break;
    default:
      break;
  }
});

document.addEventListener("keydown", (event) => {
  if (event.ctrlKey || event.metaKey || event.altKey) return;

  const key = event.key;

  if (key === "v" || key === "V") {
    event.preventDefault();
    cycleVariant(1);
    return;
  }
  if (key === "t" || key === "T") {
    event.preventDefault();
    cycleTheme(1);
    return;
  }
  if (key === "h" || key === "H") {
    event.preventDefault();
    toggleHelp();
    return;
  }
  if (key === "l" || key === "L") {
    event.preventDefault();
    toggleLanguage();
    return;
  }

  if (key === "Escape") {
    event.preventDefault();
    back();
    return;
  }

  if (key === "Enter") {
    event.preventDefault();
    select();
    return;
  }

  if (key === "ArrowLeft" || key === "a" || key === "A") {
    event.preventDefault();
    navigate("left");
    return;
  }
  if (key === "ArrowRight" || key === "d" || key === "D") {
    event.preventDefault();
    navigate("right");
    return;
  }
  if (key === "ArrowUp" || key === "w" || key === "W") {
    event.preventDefault();
    navigate("up");
    return;
  }
  if (key === "ArrowDown" || key === "s" || key === "S") {
    event.preventDefault();
    if (state.screen === "home") openSettings();
    else navigate("down");
    return;
  }

  if (state.screen === "home") {
    if (key === "p" || key === "P") {
      event.preventDefault();
      openPlayers();
    } else if (key === "q" || key === "Q") {
      event.preventDefault();
      openQuit();
    } else if (key === "c" || key === "C") {
      event.preventDefault();
      openConnecting();
    } else if (key === "e" || key === "E") {
      event.preventDefault();
      openError();
    } else if (key === "0") {
      event.preventDefault();
      if (state.emptyLibrary) closeEmpty();
      else openEmpty();
    }
  } else if (state.screen === "players") {
    if (key === "j" || key === "J") {
      event.preventDefault();
      simulateJoin();
    } else if (key === "c" || key === "C") {
      event.preventDefault();
      openConnecting();
    }
  }
});

/* ------------------------------------------------------------------ */
/* Gamepad                                                             */
/* ------------------------------------------------------------------ */

let lastButtons = [];
let lastStickMove = 0;

function pollGamepads() {
  const pads = navigator.getGamepads ? Array.from(navigator.getGamepads()) : [];
  const pad = pads.find((candidate) => candidate && candidate.connected);
  state.gamepadDetected = Boolean(pad);

  if (pad) {
    const pressed = pad.buttons.map((button) => button.pressed);
    const edge = (index) => pressed[index] && !lastButtons[index];

    if (edge(12)) navigate("up");
    if (edge(13)) navigate("down");
    if (edge(14)) navigate("left");
    if (edge(15)) navigate("right");
    if (edge(0)) select();
    if (edge(1)) back();
    if (edge(9)) {
      if (state.screen === "home") openSettings();
      else back();
    }

    const now = performance.now();
    if (now - lastStickMove > 220) {
      const axisX = pad.axes[0] || 0;
      const axisY = pad.axes[1] || 0;
      if (axisX < -0.6) {
        navigate("left");
        lastStickMove = now;
      } else if (axisX > 0.6) {
        navigate("right");
        lastStickMove = now;
      } else if (axisY < -0.6) {
        navigate("up");
        lastStickMove = now;
      } else if (axisY > 0.6) {
        navigate("down");
        lastStickMove = now;
      }
    }

    lastButtons = pressed;
  } else {
    lastButtons = [];
  }

  requestAnimationFrame(pollGamepads);
}

/* ------------------------------------------------------------------ */
/* Boot                                                                */
/* ------------------------------------------------------------------ */

render();
requestAnimationFrame(pollGamepads);
