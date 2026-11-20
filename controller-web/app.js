"use strict";

const STORAGE_KEY = "toxinator.pairing.v1";
const ADVANCED_KEY = "toxinator.advanced.v1";
const ORIENTATION_KEY = "toxinator.orientation.v1";
const PROTOCOL = 2;
const params = new URLSearchParams(window.location.search);
const queryToken = (params.get("token") || "").trim();

const BUTTON_NAMES = ["cross", "circle", "square", "triangle", "options", "l1", "r1"];
const LABEL_FALLBACK = {
  cross: "Acción",
  circle: "Volver",
  square: "",
  triangle: "",
  options: "Pausa",
  l1: "",
  r1: "",
};
const LAYOUTS = ["default", "motion", "touch"];
const ORIENTATIONS = ["auto", "portrait", "landscape"];
const DEFAULT_CONTROLLER = {
  layout: "default",
  skin: "toxinator",
  orientation: "auto",
  buttons: [...BUTTON_NAMES],
  labels: { ...LABEL_FALLBACK },
  hint: "",
  game: "",
  camera: false,
  panel: null,
};

const elements = {
  pairing: document.getElementById("pairing"),
  controller: document.getElementById("controller"),
  installButtons: [
    document.getElementById("install-button"),
    document.getElementById("install-button-2"),
  ].filter(Boolean),
  pairingStatus: document.getElementById("pairing-status"),
  pairingTitle: document.getElementById("pairing-title"),
  pairingCopy: document.getElementById("pairing-copy"),
  pairingFootCert: document.getElementById("pairing-foot-cert"),
  scanner: document.getElementById("scanner"),
  scannerVideo: document.getElementById("scanner-video"),
  scannerCanvas: document.getElementById("scanner-canvas"),
  scanButton: document.getElementById("scan-button"),
  manualToggle: document.getElementById("manual-toggle"),
  manualForm: document.getElementById("manual-form"),
  manualHost: document.getElementById("manual-host"),
  manualToken: document.getElementById("manual-token"),
  manualCancel: document.getElementById("manual-cancel"),
  pairingActions: document.getElementById("pairing-actions"),
  retryButton: document.getElementById("retry-button"),
  openConsole: document.getElementById("open-console"),
  unpairButton: document.getElementById("unpair-button"),
  pairButton: document.getElementById("pair-button"),
  settingsButton: document.getElementById("settings-button"),
  settingsSheet: document.getElementById("settings-sheet"),
  settingsClose: document.getElementById("settings-close"),
  settingsTitle: document.getElementById("settings-title"),
  orientationLock: document.getElementById("orientation-lock"),
  orientationStatus: document.getElementById("orientation-status"),
  advancedButton: document.getElementById("advanced-button"),
  calibrate: document.getElementById("calibrate"),
  enableSensors: document.getElementById("enable-sensors"),
  status: document.getElementById("status"),
  mode: document.getElementById("mode"),
  slot: document.getElementById("slot"),
  brandSubtitle: document.getElementById("brand-subtitle"),
  footHint: document.getElementById("foot-hint"),
  sensors: document.getElementById("sensors"),
  beta: document.getElementById("beta"),
  gamma: document.getElementById("gamma"),
  accel: document.getElementById("accel"),
  rtt: document.getElementById("rtt"),
  touchZone: document.getElementById("touch-zone"),
  touchHint: document.getElementById("touch-hint"),
  touchDot: document.getElementById("touch-dot"),
  stickZone: document.getElementById("stick-zone"),
  stickKnob: document.getElementById("stick-knob"),
  panel: document.getElementById("panel"),
  panelToggle: document.getElementById("panel-toggle"),
  panelTitle: document.getElementById("panel-title"),
  panelImage: document.getElementById("panel-image"),
  rotateHint: document.getElementById("rotate-hint"),
  rotateCopy: document.getElementById("rotate-copy"),
  cameraButton: document.getElementById("camera-button"),
  cameraSheet: document.getElementById("camera-sheet"),
  cameraVideo: document.getElementById("camera-video"),
  cameraCanvas: document.getElementById("camera-canvas"),
  cameraStatus: document.getElementById("camera-status"),
  cameraCapture: document.getElementById("camera-capture"),
  cameraCancel: document.getElementById("camera-cancel"),
  feedbackBanner: document.getElementById("feedback-banner"),
  feedbackTitle: document.getElementById("feedback-title"),
  feedbackCopy: document.getElementById("feedback-copy"),
  toast: document.getElementById("toast"),
};

const labels = {};
for (const name of BUTTON_NAMES) {
  labels[name] = document.getElementById(`label-${name}`);
}

const state = {
  ws: null,
  screen: "pairing",
  connected: false,
  fatal: false,
  manualDisconnect: false,
  pairing: null,
  everConnected: false,
  attempts: 0,
  slot: null,
  slotText: "SIN SLOT",
  controllerId: "",
  orientation: [0, 0, 0],
  neutral: [0, 0, 0],
  accel: [0, 0, 0],
  gyro: [0, 0, 0],
  buttons: new Set(),
  move: [0, 0],
  touch: [],
  sensorsOn: false,
  sensorRequest: false,
  mode: "launcher",
  controller: { ...DEFAULT_CONTROLLER, labels: { ...LABEL_FALLBACK } },
  advanced: false,
  orientationLock: null,
  feedbackReady: false,
  lastSent: 0,
  rtt: null,
  panel: null,
  welcomeTimer: null,
  reconnectTimer: null,
  calibrationTimer: null,
  toastTimer: null,
  deferredPrompt: null,
  installed: false,
  scanner: {
    active: false,
    stream: null,
    lastScan: 0,
  },
  camera: {
    active: false,
    stream: null,
  },
};

function round(value, digits) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

/* ---------- feedback ---------- */

function haptic(pattern) {
  if (!navigator.vibrate) return false;
  let values = pattern;
  if (typeof values === "number") values = values > 0 ? [values] : [];
  if (!Array.isArray(values)) return false;
  values = values
    .filter((value) => typeof value === "number" && Number.isFinite(value))
    .map((value) => Math.max(0, Math.min(5000, Math.round(value))))
    .slice(0, 12);
  try {
    return navigator.vibrate(values.length ? values : 0);
  } catch {
    return false;
  }
}

function buzz(milliseconds) {
  haptic(milliseconds);
}

let audioContext = null;
const activeTones = new Set();
let feedbackPulseTimer = null;

function pulseFeedback() {
  if (!elements.touchZone) return;
  elements.touchZone.classList.remove("feedback-pulse");
  void elements.touchZone.offsetWidth;
  elements.touchZone.classList.add("feedback-pulse");
  if (feedbackPulseTimer !== null) window.clearTimeout(feedbackPulseTimer);
  feedbackPulseTimer = window.setTimeout(() => {
    feedbackPulseTimer = null;
    elements.touchZone.classList.remove("feedback-pulse");
  }, 190);
}

function ensureAudio() {
  if (audioContext) return audioContext;
  const AudioCtor = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtor) return null;
  try {
    audioContext = new AudioCtor();
  } catch {
    return null;
  }
  return audioContext;
}

function unlockAudio() {
  const context = ensureAudio();
  if (context && context.state === "suspended") {
    context.resume().catch(() => {});
  }
}

function playTone(frequency, duration, volume) {
  const context = ensureAudio();
  if (!context) return;
  if (context.state === "suspended") {
    context.resume().catch(() => {});
  }
  const now = context.currentTime;
  const durationMs = Math.max(20, Math.min(5000, Number(duration) || 120));
  const frequencyHz = Math.max(40, Math.min(12000, Number(frequency) || 440));
  const gainValue = Math.max(0, Math.min(1, Number(volume) || 0.35));
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(frequencyHz, now);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, gainValue), now + 0.012);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + durationMs / 1000);
  oscillator.connect(gain).connect(context.destination);
  oscillator.start(now);
  oscillator.stop(now + durationMs / 1000 + 0.025);
  activeTones.add(oscillator);
  oscillator.onended = () => activeTones.delete(oscillator);
}

function stopAudio() {
  for (const oscillator of activeTones) {
    try {
      oscillator.stop();
    } catch {
      // already stopped
    }
  }
  activeTones.clear();
}

function applyFeedback(message) {
  pulseFeedback();
  if (message.type === "haptic") {
    haptic(message.pattern);
    return;
  }
  if (message.type !== "audio") return;
  if (message.action === "stop") {
    stopAudio();
    return;
  }
  if (message.action === "tone") {
    playTone(message.frequency, message.duration, message.volume);
  }
}

function feedbackHint() {
  const userAgent = navigator.userAgent || "";
  const ios =
    /iPad|iPhone|iPod/i.test(userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const firefoxAndroid = /Android/i.test(userAgent) && /Firefox|Focus/i.test(userAgent);
  const hasVibration = typeof navigator.vibrate === "function";
  if (ios) {
    return {
      title: "ACTIVAR SONIDO",
      copy: "iPhone no permite vibrar desde la web; tocá para activar el audio.",
      vibration: false,
      ios: true,
      firefox: false,
    };
  }
  if (firefoxAndroid) {
    return {
      title: "ACTIVAR SONIDO",
      copy: "Firefox Android no vibra; abrí el QR en Chrome para sentir la vibración.",
      vibration: false,
      ios: false,
      firefox: true,
    };
  }
  if (!hasVibration) {
    return {
      title: "ACTIVAR SONIDO",
      copy: "Este navegador no expone vibración; tocá para activar el audio.",
      vibration: false,
      ios: false,
      firefox: false,
    };
  }
  return {
    title: "ACTIVAR SONIDO Y VIBRACIÓN",
    copy: "Tocá acá para probar el parlante y la vibración.",
    vibration: true,
    ios: false,
    firefox: false,
  };
}

function updateFeedbackBanner() {
  if (!elements.feedbackBanner) return;
  const hint = feedbackHint();
  if (elements.feedbackTitle) elements.feedbackTitle.textContent = hint.title;
  if (elements.feedbackCopy) elements.feedbackCopy.textContent = hint.copy;
  elements.feedbackBanner.hidden =
    state.screen !== "controller" || state.mode === "launcher" || state.feedbackReady;
}

function activateFeedback() {
  unlockAudio();
  const hint = feedbackHint();
  const audio = Boolean(ensureAudio());
  const vibrated = hint.vibration ? haptic([250, 100, 400]) : false;
  if (audio) {
    playTone(660, 110, 0.35);
    window.setTimeout(() => playTone(880, 150, 0.3), 140);
  }
  state.feedbackReady = true;
  updateFeedbackBanner();
  if (!audio && !hint.vibration) {
    showToast("Este navegador no permite sonido ni vibración", "warn", 4200);
  } else if (!audio) {
    showToast("Vibración activada · audio no disponible", "warn", 4200);
  } else if (hint.ios) {
    showToast("Audio activado · iPhone no permite vibrar desde la web", "warn", 6000);
  } else if (hint.firefox) {
    showToast("Audio activado · Firefox Android no vibra; abrí el QR en Chrome", "warn", 6000);
  } else if (!hint.vibration) {
    showToast("Audio activado · este navegador no expone vibración", "warn", 6000);
  } else if (vibrated === false) {
    showToast("Audio activado · el navegador no dejó vibrar", "warn", 4200);
  } else {
    showToast("Sonido y vibración activados");
  }
}

/* ---------- status / toast ---------- */

function setStatus(text, kind) {
  if (!elements.status) return;
  elements.status.textContent = text;
  elements.status.classList.remove("online", "offline", "warn", "error");
  if (kind) elements.status.classList.add(kind);
}

function setSlot(text) {
  state.slotText = text;
  if (elements.slot) {
    elements.slot.textContent = state.advanced ? text : text.split(" · ")[0];
  }
}

function setPairingStatus(text, kind = "") {
  elements.pairingStatus.textContent = text;
  elements.pairingStatus.classList.remove("warn", "error", "working");
  if (kind) elements.pairingStatus.classList.add(kind);
}

function showToast(message, kind = "", duration = 1900) {
  elements.toast.textContent = message;
  elements.toast.classList.remove("warn", "error");
  if (kind) elements.toast.classList.add(kind);
  elements.toast.classList.add("show");
  if (state.toastTimer !== null) window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => {
    state.toastTimer = null;
    elements.toast.classList.remove("show");
  }, duration);
}

/* ---------- mode / profile ---------- */

function applyMode(mode) {
  state.mode = mode === "game" ? "game" : "launcher";
  if (state.mode === "launcher") stopAudio();
  updateFeedbackBanner();
  if (state.screen === "controller") {
    const launcher = state.mode === "launcher";
    document.body.classList.toggle("mode-launcher", launcher);
    document.body.classList.toggle("mode-game", !launcher);
    if (elements.mode) elements.mode.textContent = launcher ? "LAUNCHER" : "JUEGO";
    renderControllerChrome();
    updatePanelVisibility();
    updateCameraButton();
    if (!launcher && state.connected) startSensorsIfPossible();
  }
}

function normalizeLabels(source) {
  const result = { ...LABEL_FALLBACK };
  if (!source || typeof source !== "object") return result;
  for (const name of BUTTON_NAMES) {
    const value = source[name];
    if (typeof value === "string" && value.trim()) {
      result[name] = value.trim().slice(0, 24);
    }
  }
  return result;
}

function normalizePanel(source) {
  if (!source || typeof source !== "object") return null;
  if (typeof source.url !== "string" || !source.url) return null;
  return {
    title: typeof source.title === "string" ? source.title.slice(0, 40) : "",
    url: source.url,
    fit: source.fit === "cover" || source.fit === "stretch" ? source.fit : "contain",
  };
}

function applyController(profile) {
  const source = profile && typeof profile === "object" ? profile : {};
  const layout = LAYOUTS.includes(source.layout)
    ? source.layout
    : DEFAULT_CONTROLLER.layout;
  const orientation = ORIENTATIONS.includes(source.orientation)
    ? source.orientation
    : DEFAULT_CONTROLLER.orientation;
  const available = Array.isArray(source.buttons)
    ? BUTTON_NAMES.filter((name) => source.buttons.includes(name))
    : [...BUTTON_NAMES];
  state.controller = {
    layout,
    skin: "toxinator",
    orientation,
    buttons: available,
    labels: normalizeLabels(source.labels),
    hint: typeof source.hint === "string" ? source.hint.trim().slice(0, 80) : "",
    game: typeof source.game === "string" ? source.game.slice(0, 60) : "",
    camera: source.camera === true,
    panel: normalizePanel(source.panel),
  };
  document.body.dataset.layout = layout;
  document.body.dataset.skin = "toxinator";
  for (const element of buttonElements) {
    const name = element.dataset.button;
    element.hidden = name ? !available.includes(name) : element.hidden;
  }
  state.panel = state.controller.panel;
  applyPanel(state.panel);
  updateOrientation();
  renderControllerChrome();
  updateCameraButton();
}

function applyPanel(panel) {
  if (!elements.panel) return;
  if (!panel) {
    elements.panel.hidden = true;
    return;
  }
  state.panel = panel;
  elements.panel.hidden = state.mode === "launcher";
  elements.panel.dataset.fit = panel.fit;
  elements.panelTitle.textContent = panel.title || "PANEL";
  if (elements.panelImage.getAttribute("src") !== panel.url) {
    elements.panelImage.src = panel.url;
  }
  elements.panel.classList.remove("expanded");
  elements.panelToggle.setAttribute("aria-expanded", "false");
}

function updatePanelVisibility() {
  if (!elements.panel) return;
  elements.panel.hidden = state.mode === "launcher" || !state.panel;
}

function updateCameraButton() {
  if (!elements.cameraButton) return;
  elements.cameraButton.hidden =
    !state.controller.camera || state.mode !== "game" || !state.connected;
}

function layoutHint(layout) {
  if (layout === "motion") return "Incliná el teléfono o usá el stick";
  if (layout === "touch") return "Arrastrá para apuntar";
  return "Stick para mover · arrastrá para apuntar";
}

function layoutFoot(layout) {
  if (layout === "motion") return "MOVIMIENTO · STICK OPCIONAL";
  if (layout === "touch") return "TOUCH · × ACCIÓN";
  return "STICK · × ACCIÓN";
}

function renderControllerChrome() {
  const launcher = state.mode === "launcher";
  const controller = state.controller;
  if (elements.brandSubtitle) {
    elements.brandSubtitle.textContent = launcher
      ? "MANDO · TOXINATOR"
      : controller.game
        ? controller.game.toUpperCase()
        : "MANDO · JUEGO";
  }
  const activeLabels = launcher
    ? { cross: "Elegir", circle: "Atrás", square: "", triangle: "", options: "" }
    : controller.labels;
  for (const name of BUTTON_NAMES) {
    if (!labels[name]) continue;
    labels[name].textContent = activeLabels[name] || "";
  }
  if (elements.footHint) {
    elements.footHint.textContent = launcher
      ? "STICK O MOUSE · × ELEGIR"
      : controller.hint || layoutFoot(controller.layout);
  }
  if (elements.touchHint) {
    elements.touchHint.textContent = launcher
      ? "Arrastrá o usá el stick"
      : layoutHint(controller.layout);
  }
}

/* ---------- orientation ---------- */

const portraitQuery = window.matchMedia("(orientation: portrait)");

function deviceOrientation() {
  return portraitQuery.matches ? "portrait" : "landscape";
}

function updateOrientation() {
  const device = deviceOrientation();
  const required = state.controller.orientation;
  const layout = state.orientationLock
    ? state.orientationLock
    : required === "auto"
      ? device
      : required;
  document.body.dataset.orientation = layout;
  const mismatch =
    !state.orientationLock && required !== "auto" && required !== device;
  if (elements.rotateHint) elements.rotateHint.hidden = !mismatch;
  if (elements.rotateCopy) {
    elements.rotateCopy.textContent =
      required === "landscape" ? "Este juego pide horizontal." : "Este juego pide vertical.";
  }
  if (elements.orientationStatus) {
    elements.orientationStatus.textContent = state.orientationLock
      ? `BLOQUEADA · ${layout === "portrait" ? "VERTICAL" : "HORIZONTAL"}`
      : `AUTO · ${device === "portrait" ? "VERTICAL" : "HORIZONTAL"}`;
  }
  if (elements.orientationLock) {
    elements.orientationLock.textContent = state.orientationLock ? "LIBERAR" : "BLOQUEAR";
    elements.orientationLock.classList.toggle("active", Boolean(state.orientationLock));
  }
}

function toggleOrientationLock() {
  if (state.orientationLock) {
    state.orientationLock = null;
    saveOrientationLock(null);
    showToast("Orientación automática");
  } else {
    state.orientationLock = document.body.dataset.orientation || deviceOrientation();
    saveOrientationLock(state.orientationLock);
    showToast(`Orientación ${state.orientationLock === "portrait" ? "vertical" : "horizontal"} fija`);
  }
  updateOrientation();
}

function loadOrientationLock() {
  try {
    const stored = window.localStorage.getItem(ORIENTATION_KEY);
    return stored === "portrait" || stored === "landscape" ? stored : null;
  } catch {
    return null;
  }
}

function saveOrientationLock(value) {
  try {
    if (value) window.localStorage.setItem(ORIENTATION_KEY, value);
    else window.localStorage.removeItem(ORIENTATION_KEY);
  } catch {
    // private mode: the lock still applies for this session
  }
}

/* ---------- advanced ---------- */

function loadAdvanced() {
  try {
    return window.localStorage.getItem(ADVANCED_KEY) === "1";
  } catch {
    return false;
  }
}

function saveAdvanced(enabled) {
  try {
    window.localStorage.setItem(ADVANCED_KEY, enabled ? "1" : "0");
  } catch {
    // private mode
  }
}

function applyAdvanced(enabled, { persist = false } = {}) {
  state.advanced = Boolean(enabled);
  document.body.classList.toggle("advanced", state.advanced);
  if (elements.advancedButton) {
    elements.advancedButton.textContent = state.advanced ? "OCULTAR" : "MOSTRAR";
    elements.advancedButton.classList.toggle("active", state.advanced);
  }
  setSlot(state.slotText);
  if (persist) saveAdvanced(state.advanced);
}

/* ---------- pairing storage ---------- */

function loadPairing() {
  try {
    const data = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null");
    if (data && typeof data.host === "string" && typeof data.token === "string") {
      if (data.host && data.token) {
        return {
          host: data.host,
          token: data.token,
          secure: data.secure !== false,
          origin: data.origin || `${data.secure === false ? "http" : "https"}://${data.host}/`,
        };
      }
    }
  } catch {
    // ignore corrupt storage
  }
  return null;
}

function savePairing(pairing) {
  state.pairing = pairing;
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        host: pairing.host,
        token: pairing.token,
        secure: pairing.secure,
        origin: pairing.origin,
        saved_at: new Date().toISOString(),
      })
    );
  } catch {
    // private mode or quota
  }
}

function clearPairing() {
  state.pairing = null;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

function parsePairing(text, tokenFallback = "", defaultScheme = "") {
  const value = String(text || "").trim();
  if (!value) {
    return { error: "Ingresá la IP o la URL de la consola." };
  }
  const hasScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(value);
  const fallbackScheme =
    defaultScheme || (window.location.protocol === "https:" ? "https" : "http");
  const candidate = hasScheme ? value : `${fallbackScheme}://${value}`;
  let url;
  try {
    url = new URL(candidate);
  } catch {
    return { error: "La dirección de la consola no es válida." };
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    return { error: "La dirección tiene que empezar con http:// o https://." };
  }
  let host = url.host;
  if (!hasScheme && !url.port) host = `${url.host}:8443`;
  const token = (url.searchParams.get("token") || tokenFallback || "").trim();
  if (!token) {
    return { error: "Falta el token. Escaneá el QR o pegalo a mano." };
  }
  const secure = url.protocol !== "http:";
  return {
    host,
    token,
    secure,
    origin: `${url.protocol}//${host}/`,
  };
}

function fillManual() {
  if (state.pairing) {
    elements.manualHost.value = state.pairing.host;
    elements.manualToken.value = state.pairing.token;
  } else {
    elements.manualHost.value = "";
    elements.manualToken.value = "";
  }
}

function showPairing(message, kind = "") {
  stopAudio();
  closeSettings();
  stopCamera();
  state.screen = "pairing";
  updateFeedbackBanner();
  document.body.classList.remove("mode-launcher", "mode-game");
  document.body.classList.add("mode-pairing");
  elements.pairing.hidden = false;
  elements.controller.hidden = true;
  const hasPairing = Boolean(state.pairing);
  elements.retryButton.hidden = !hasPairing;
  elements.openConsole.hidden = !hasPairing;
  elements.unpairButton.hidden = !hasPairing;
  fillManual();
  if (message) setPairingStatus(message, kind);
}

function showController() {
  state.screen = "controller";
  elements.pairing.hidden = true;
  elements.controller.hidden = false;
  document.body.classList.remove("mode-pairing");
  applyMode(state.mode);
  updateReadout();
  startSensorsIfPossible();
}

function secureContext() {
  return window.isSecureContext === true;
}

function updatePairingMode() {
  if (secureContext()) return;
  elements.pairingTitle.innerHTML = "ABRÍ EL ENLACE<br>DEL QR";
  elements.pairingCopy.innerHTML =
    "En la consola el QR aparece solo. Escanealo con la cámara del teléfono " +
    "y abrí el enlace. También podés ingresar IP y token.";
  elements.pairingFootCert.textContent = "MODO HTTP · SIN CERTIFICADO";
  elements.scanButton.hidden = true;
  elements.manualToggle.classList.remove("secondary");
  elements.manualToggle.classList.add("primary");
  for (const button of elements.installButtons) button.hidden = true;
}

function pairingUrl(pairing) {
  const scheme = pairing.secure ? "https" : "http";
  return `${scheme}://${pairing.host}/`;
}

async function probePairing(pairing) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 3500);
  try {
    await fetch(pairingUrl(pairing), {
      method: "GET",
      mode: "no-cors",
      cache: "no-store",
      signal: controller.signal,
    });
    return true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

async function diagnosePairing(target) {
  const pairing = state.pairing;
  if (!pairing) return;
  const reachable = await probePairing(pairing);
  if (
    state.ws !== null ||
    state.fatal ||
    state.manualDisconnect ||
    state.screen !== "pairing" ||
    state.pairing !== pairing
  ) {
    return;
  }
  if (reachable) {
    setPairingStatus(
      `La consola responde en ${target}, pero el mando no conectó. ` +
        "Probá de nuevo; si cambió el token, escaneá el QR nuevo.",
      "error"
    );
  } else if (pairing.secure) {
    setPairingStatus(
      `No pude llegar a ${target}. Revisá la Wi-Fi y el firewall. ` +
        `Si cambió la IP, escaneá el QR nuevo. Si es la primera vez, ` +
        `abrí ${pairingUrl(pairing)} en el navegador y aceptá el certificado.`,
      "error"
    );
  } else {
    setPairingStatus(
      `No pude llegar a ${target}. Revisá que la consola esté encendida, ` +
        "en la misma Wi-Fi, y el firewall. Si cambió la IP, escaneá el QR nuevo.",
      "error"
    );
  }
}

/* ---------- readout / send ---------- */

function updateReadout() {
  const beta = (state.orientation[1] || 0) - (state.neutral[1] || 0);
  const gamma = (state.orientation[2] || 0) - (state.neutral[2] || 0);
  const magnitude = Math.hypot(state.accel[0], state.accel[1], state.accel[2]);
  if (elements.beta) elements.beta.textContent = `${beta.toFixed(0)}°`;
  if (elements.gamma) elements.gamma.textContent = `${gamma.toFixed(0)}°`;
  if (elements.accel) elements.accel.textContent = magnitude.toFixed(1);
  if (elements.rtt) {
    elements.rtt.textContent = state.rtt === null ? "—" : `${Math.round(state.rtt)} ms`;
  }
  if (elements.sensors) {
    let text = "SENSORES OFF";
    if (state.sensorsOn) text = "SENSORES ON";
    else if (!secureContext()) text = "SENSORES · HTTPS";
    else if (needsPermission()) text = "SENSORES · TOCÁ";
    elements.sensors.textContent = text;
    elements.sensors.classList.toggle("on", state.sensorsOn);
  }
}

function send(message) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(message));
  }
}

function clearReconnect() {
  if (state.reconnectTimer !== null) {
    window.clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }
}

function resetInputs() {
  state.buttons.clear();
  state.move = [0, 0];
  state.touch = [];
  stickPointer = null;
  touchPointer = null;
  for (const element of buttonElements) element.classList.remove("pressed");
  if (elements.stickKnob) {
    elements.stickKnob.style.transform = "translate(-50%, -50%)";
  }
  if (elements.touchDot) elements.touchDot.hidden = true;
}

function closeSocket() {
  clearReconnect();
  stopAudio();
  stopCamera();
  if (state.welcomeTimer !== null) {
    window.clearTimeout(state.welcomeTimer);
    state.welcomeTimer = null;
  }
  if (state.ws) {
    const ws = state.ws;
    state.ws = null;
    try {
      ws.close();
    } catch {
      // already closed
    }
  }
  resetInputs();
}

function scheduleReconnect() {
  if (state.reconnectTimer !== null || state.manualDisconnect || state.fatal) return;
  const delay = Math.min(1200 + state.attempts * 450, 3200);
  state.reconnectTimer = window.setTimeout(() => {
    state.reconnectTimer = null;
    connect();
  }, delay);
}

function connect() {
  if (!state.pairing) {
    showPairing("Sin consola vinculada. Escaneá el QR de la consola.");
    return;
  }
  if (state.ws && state.ws.readyState <= WebSocket.OPEN) return;

  if (window.location.protocol === "https:" && !state.pairing.secure) {
    showPairing(
      `La consola está en HTTP. Abrí ${pairingUrl(state.pairing)} en el navegador del celular.`,
      "error"
    );
    return;
  }

  const scheme = state.pairing.secure ? "wss:" : "ws:";
  let ws;
  try {
    ws = new WebSocket(`${scheme}//${state.pairing.host}/ws`);
  } catch {
    showPairing(`No pude abrir la conexión con ${state.pairing.host}.`, "error");
    return;
  }

  state.ws = ws;
  state.connected = false;
  state.fatal = false;
  state.manualDisconnect = false;
  if (state.welcomeTimer !== null) window.clearTimeout(state.welcomeTimer);
  state.welcomeTimer = window.setTimeout(() => {
    state.welcomeTimer = null;
    if (!state.connected && state.ws === ws) ws.close();
  }, 5000);

  if (state.screen === "controller") {
    setStatus("Reconectando…", "warn");
  } else {
    setPairingStatus(`Conectando a ${state.pairing.host}…`, "working");
  }

  ws.addEventListener("open", () => {
    ws.send(
      JSON.stringify({
        type: "hello",
        token: state.pairing ? state.pairing.token : "",
        name: (navigator.userAgent || "phone").slice(0, 80),
        protocol: PROTOCOL,
      })
    );
  });

  ws.addEventListener("message", (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch {
      return;
    }
    if (message.type === "welcome") {
      if (state.welcomeTimer !== null) {
        window.clearTimeout(state.welcomeTimer);
        state.welcomeTimer = null;
      }
      state.connected = true;
      state.fatal = false;
      state.everConnected = true;
      state.attempts = 0;
      state.slot = message.slot;
      state.controllerId = message.controller_id || "";
      setStatus(`P${message.slot + 1} conectado`, "online");
      setSlot(`P${message.slot + 1} · ${state.controllerId}`);
      stopScanner();
      showController();
      updateCameraButton();
      buzz(18);
    } else if (message.type === "mode") {
      applyMode(message.mode);
    } else if (message.type === "controller") {
      applyController(message.profile);
    } else if (message.type === "panel") {
      applyPanel(normalizePanel(message.panel));
    } else if (message.type === "haptic" || message.type === "audio") {
      applyFeedback(message);
    } else if (message.type === "error") {
      state.fatal = true;
      let text = "Error de conexión.";
      if (message.code === "full") {
        text = "La consola ya tiene 4 mandos conectados.";
      } else if (message.code === "bad-token") {
        text = "Token inválido. Escaneá el QR de la consola otra vez.";
      } else if (message.code === "bad-protocol") {
        text = "El mando y la consola hablan versiones distintas. Recargá la página.";
      }
      showPairing(text, "error");
      if (message.code === "bad-token") {
        elements.retryButton.hidden = true;
        elements.openConsole.hidden = true;
      }
      ws.close();
    } else if (message.type === "pong") {
      if (typeof message.t === "number") {
        state.rtt = Math.max(0, performance.now() - message.t);
        updateReadout();
      }
    } else if (message.type === "calibrated") {
      if (state.calibrationTimer !== null) {
        window.clearTimeout(state.calibrationTimer);
        state.calibrationTimer = null;
      }
      setStatus("Pose guardada", "online");
      showToast("Pose guardada");
      window.setTimeout(() => {
        if (state.connected) setStatus(`P${state.slot + 1} conectado`, "online");
      }, 1200);
    }
  });

  ws.addEventListener("close", () => {
    if (state.ws !== ws) return;
    state.ws = null;
    state.connected = false;
    resetInputs();
    updateCameraButton();
    if (state.welcomeTimer !== null) {
      window.clearTimeout(state.welcomeTimer);
      state.welcomeTimer = null;
    }
    if (state.manualDisconnect || state.fatal) return;

    state.attempts += 1;
    const target = state.pairing ? state.pairing.host : "la consola";
    if (state.everConnected && state.attempts <= 4) {
      setStatus("Reconectando…", "warn");
      scheduleReconnect();
      return;
    }

    state.everConnected = false;
    showPairing(`Buscando la consola en ${target}…`, "working");
    void diagnosePairing(target);
  });

  ws.addEventListener("error", () => {
    ws.close();
  });
}

/* ---------- sensors ---------- */

function startSensors() {
  if (state.sensorsOn) return;
  state.sensorsOn = true;
  elements.enableSensors.classList.add("hidden");
  updateReadout();

  window.addEventListener(
    "deviceorientation",
    (event) => {
      state.orientation = [event.alpha || 0, event.beta || 0, event.gamma || 0];
      updateReadout();
    },
    { passive: true }
  );

  window.addEventListener(
    "devicemotion",
    (event) => {
      const acceleration = event.accelerationIncludingGravity || {};
      state.accel = [acceleration.x || 0, acceleration.y || 0, acceleration.z || 0];
      const rotation = event.rotationRate || {};
      state.gyro = [rotation.alpha || 0, rotation.beta || 0, rotation.gamma || 0];
      updateReadout();
    },
    { passive: true }
  );
}

function needsPermission() {
  return (
    typeof window.DeviceMotionEvent !== "undefined" &&
    typeof window.DeviceMotionEvent.requestPermission === "function"
  );
}

function startSensorsIfPossible() {
  if (state.sensorsOn) return;
  if (!secureContext() || needsPermission()) {
    updateReadout();
    return;
  }
  startSensors();
}

function requestSensorPermission() {
  const requests = [];
  if (
    typeof window.DeviceMotionEvent !== "undefined" &&
    typeof window.DeviceMotionEvent.requestPermission === "function"
  ) {
    requests.push(window.DeviceMotionEvent.requestPermission());
  }
  if (
    typeof window.DeviceOrientationEvent !== "undefined" &&
    typeof window.DeviceOrientationEvent.requestPermission === "function"
  ) {
    requests.push(window.DeviceOrientationEvent.requestPermission());
  }
  return Promise.all(requests);
}

async function enableSensors({ silent = false } = {}) {
  if (state.sensorsOn || state.sensorRequest) return;
  if (!secureContext()) {
    showToast("Los sensores necesitan HTTPS", "warn", 4200);
    return;
  }
  state.sensorRequest = true;
  try {
    if (needsPermission()) {
      const results = await requestSensorPermission();
      if (results.some((result) => result !== "granted")) {
        setStatus("Sensores bloqueados", "warn");
        showToast("Sensores bloqueados", "error");
        updateReadout();
        return;
      }
    }
    startSensors();
    if (!silent) showToast("Sensores activados");
  } catch {
    setStatus("Sensores bloqueados", "warn");
    showToast("No pude activar los sensores", "error");
    updateReadout();
  } finally {
    state.sensorRequest = false;
  }
}

function autoEnableSensors(event) {
  if (state.screen !== "controller" || state.sensorsOn) return;
  if (!secureContext() || !needsPermission()) return;
  document.removeEventListener("pointerdown", autoEnableSensors, true);
  void enableSensors({ silent: true });
}

/* ---------- scanner ---------- */

function stopScanner() {
  const scanner = state.scanner;
  scanner.active = false;
  scanner.lastScan = 0;
  if (scanner.stream) {
    for (const track of scanner.stream.getTracks()) track.stop();
    scanner.stream = null;
  }
  if (elements.scannerVideo) {
    try {
      elements.scannerVideo.pause();
    } catch {
      // ignore
    }
    elements.scannerVideo.srcObject = null;
  }
  elements.scanner.hidden = true;
  elements.scanButton.textContent = "ESCANEAR QR";
  elements.scanButton.disabled = false;
  elements.manualToggle.hidden = false;
}

async function startScanner() {
  if (state.scanner.active) return;
  if (!secureContext()) {
    setPairingStatus(
      "La cámara necesita HTTPS. En modo HTTP abrí el enlace del QR o ingresá IP y token.",
      "warn"
    );
    toggleManual(true);
    return;
  }
  if (typeof window.jsQR !== "function") {
    setPairingStatus("El escáner no está disponible. Ingresá los datos a mano.", "error");
    toggleManual(true);
    return;
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setPairingStatus("Este navegador no da acceso a la cámara.", "error");
    toggleManual(true);
    return;
  }

  elements.scanButton.disabled = true;
  elements.scanButton.textContent = "ABRIENDO CÁMARA…";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
    });
    state.scanner.stream = stream;
    state.scanner.active = true;
    state.scanner.lastScan = 0;
    elements.scanner.hidden = false;
    elements.scannerVideo.srcObject = stream;
    await elements.scannerVideo.play();
    elements.scanButton.disabled = false;
    elements.scanButton.textContent = "CANCELAR ESCANEO";
    elements.manualToggle.hidden = true;
    setPairingStatus("Buscando el QR de la consola…", "working");
    window.requestAnimationFrame(scanFrame);
  } catch (error) {
    stopScanner();
    const denied =
      error &&
      (error.name === "NotAllowedError" ||
        error.name === "SecurityError" ||
        error.name === "NotFoundError");
    setPairingStatus(
      denied
        ? "No pude usar la cámara. Revisá el permiso o ingresá los datos a mano."
        : "No pude abrir la cámara. Ingresá los datos a mano.",
      "error"
    );
  }
}

function scanFrame(now) {
  if (!state.scanner.active) return;
  window.requestAnimationFrame(scanFrame);
  if (now - state.scanner.lastScan < 140) return;
  state.scanner.lastScan = now;

  const video = elements.scannerVideo;
  if (!video || !video.videoWidth || !video.videoHeight) return;

  const canvas = elements.scannerCanvas;
  const longest = Math.max(video.videoWidth, video.videoHeight);
  const scale = Math.min(1, 640 / longest);
  const width = Math.round(video.videoWidth * scale);
  const height = Math.round(video.videoHeight * scale);
  if (canvas.width !== width) canvas.width = width;
  if (canvas.height !== height) canvas.height = height;

  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return;
  context.drawImage(video, 0, 0, width, height);

  let code = null;
  try {
    const image = context.getImageData(0, 0, width, height);
    code = window.jsQR(image.data, width, height, { inversionAttempts: "dontInvert" });
  } catch {
    return;
  }
  if (code && code.data) handleScanned(code.data);
}

function handleScanned(text) {
  const pairing = parsePairing(text);
  if (pairing.error) {
    setPairingStatus("Ese QR no es de Toxinator. Probá otra vez.", "error");
    state.scanner.lastScan = performance.now() + 1200;
    return;
  }
  stopScanner();
  savePairing(pairing);
  fillManual();
  elements.retryButton.hidden = false;
  elements.openConsole.hidden = false;
  elements.unpairButton.hidden = false;
  buzz(35);
  closeSocket();
  state.fatal = false;
  state.manualDisconnect = false;
  state.everConnected = false;
  state.attempts = 0;
  setPairingStatus(`Consola encontrada: ${pairing.host}. Conectando…`, "working");
  connect();
}

function toggleManual(show) {
  elements.manualForm.hidden = !show;
  elements.pairingActions.hidden = show;
  if (show) {
    fillManual();
    window.setTimeout(() => elements.manualHost.focus(), 50);
  }
}

function updateInstallButtons() {
  if (!secureContext()) {
    for (const button of elements.installButtons) button.hidden = true;
    return;
  }
  const standalone =
    state.installed ||
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  for (const button of elements.installButtons) button.hidden = standalone;
}

async function promptInstall() {
  if (!state.deferredPrompt) {
    showToast("Chrome: menú ⋮ → Instalar app. Necesita HTTPS con certificado de confianza.", "warn");
    return;
  }
  const prompt = state.deferredPrompt;
  state.deferredPrompt = null;
  prompt.prompt();
  try {
    await prompt.userChoice;
  } catch {
    // ignored
  }
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator) || !secureContext()) return;
  navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
    // Self-signed certificate or unsupported browser: the app still works online.
  });
}

/* ---------- input: buttons ---------- */

const buttonElements = Array.from(document.querySelectorAll("[data-button]"));

function pressButton(name) {
  if (!name) return;
  if (state.buttons.has(name)) return;
  state.buttons.add(name);
  for (const element of buttonElements) {
    if (element.dataset.button === name) element.classList.add("pressed");
  }
  buzz(10);
}

function releaseButton(name) {
  state.buttons.delete(name);
  for (const element of buttonElements) {
    if (element.dataset.button === name) element.classList.remove("pressed");
  }
}

for (const element of buttonElements) {
  const name = element.dataset.button;
  element.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    try {
      element.setPointerCapture(event.pointerId);
    } catch {
      // some browsers reject capture for synthetic events
    }
    pressButton(name);
  });
  const release = (event) => {
    event.preventDefault();
    releaseButton(name);
  };
  element.addEventListener("pointerup", release);
  element.addEventListener("pointercancel", release);
  element.addEventListener("lostpointercapture", release);
  element.addEventListener("contextmenu", (event) => event.preventDefault());
}

/* ---------- input: stick ---------- */

const STICK_DEADZONE = 0.18;
let stickPointer = null;

function stickRadius(rect) {
  return Math.min(rect.width, rect.height) * 0.5 * 0.78;
}

function setStick(event) {
  if (!elements.stickZone) return;
  const rect = elements.stickZone.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const radius = Math.max(1, stickRadius(rect));
  let dx = (event.clientX - centerX) / radius;
  let dy = (centerY - event.clientY) / radius;
  const length = Math.hypot(dx, dy);
  if (length > 1) {
    dx /= length;
    dy /= length;
  }
  if (Math.hypot(dx, dy) < STICK_DEADZONE) {
    state.move = [0, 0];
  } else {
    state.move = [round(dx, 3), round(dy, 3)];
  }
  const knob = elements.stickKnob;
  if (knob) {
    const limit = Math.max(0, Math.min(rect.width, rect.height) / 2 - knob.offsetWidth / 2);
    knob.style.transform = `translate(calc(-50% + ${dx * limit}px), calc(-50% + ${-dy * limit}px))`;
  }
}

function endStick(event) {
  if (event && event.pointerId !== stickPointer) return;
  stickPointer = null;
  state.move = [0, 0];
  if (elements.stickKnob) {
    elements.stickKnob.style.transform = "translate(-50%, -50%)";
  }
}

if (elements.stickZone) {
  elements.stickZone.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    stickPointer = event.pointerId;
    try {
      elements.stickZone.setPointerCapture(event.pointerId);
    } catch {
      // ignore
    }
    if (elements.touchHint) elements.touchHint.classList.add("hidden");
    setStick(event);
  });
  elements.stickZone.addEventListener("pointermove", (event) => {
    if (event.pointerId !== stickPointer) return;
    event.preventDefault();
    setStick(event);
  });
  elements.stickZone.addEventListener("pointerup", endStick);
  elements.stickZone.addEventListener("pointercancel", endStick);
  elements.stickZone.addEventListener("lostpointercapture", endStick);
  elements.stickZone.addEventListener("contextmenu", (event) => event.preventDefault());
}

/* ---------- input: touch zone ---------- */

let touchPointer = null;

function setTouch(event) {
  if (!elements.touchZone) return;
  const rect = elements.touchZone.getBoundingClientRect();
  const x = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  const y = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
  state.touch = [{ id: 0, x: round(x, 3), y: round(y, 3), pressure: 1 }];
  if (elements.touchDot) {
    elements.touchDot.hidden = false;
    elements.touchDot.style.left = `${x * 100}%`;
    elements.touchDot.style.top = `${y * 100}%`;
  }
  if (elements.touchHint) elements.touchHint.classList.add("hidden");
}

function endTouch(event) {
  if (event && event.pointerId !== touchPointer) return;
  touchPointer = null;
  state.touch = [];
  if (elements.touchDot) elements.touchDot.hidden = true;
}

if (elements.touchZone) {
  elements.touchZone.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    touchPointer = event.pointerId;
    try {
      elements.touchZone.setPointerCapture(event.pointerId);
    } catch {
      // ignore
    }
    setTouch(event);
  });
  elements.touchZone.addEventListener("pointermove", (event) => {
    if (event.pointerId !== touchPointer) return;
    event.preventDefault();
    setTouch(event);
  });
  elements.touchZone.addEventListener("pointerup", endTouch);
  elements.touchZone.addEventListener("pointercancel", endTouch);
  elements.touchZone.addEventListener("lostpointercapture", endTouch);
  elements.touchZone.addEventListener("contextmenu", (event) => event.preventDefault());
}

/* ---------- camera ---------- */

async function openCamera() {
  if (!secureContext()) {
    showToast("La cámara necesita HTTPS con certificado aceptado", "error", 4200);
    return;
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showToast("Este navegador no da acceso a la cámara", "error");
    return;
  }
  elements.cameraSheet.hidden = false;
  elements.cameraStatus.textContent = "Abriendo cámara…";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: { ideal: "user" },
        width: { ideal: 1280 },
        height: { ideal: 1280 },
      },
    });
    state.camera.stream = stream;
    state.camera.active = true;
    elements.cameraVideo.srcObject = stream;
    await elements.cameraVideo.play();
    elements.cameraStatus.textContent = "Encuadrá la cara dentro del círculo.";
  } catch (error) {
    const denied =
      error &&
      (error.name === "NotAllowedError" ||
        error.name === "SecurityError" ||
        error.name === "NotFoundError");
    elements.cameraStatus.textContent = denied
      ? "No pude usar la cámara. Revisá el permiso del navegador."
      : "No pude abrir la cámara.";
  }
}

function stopCamera() {
  state.camera.active = false;
  if (state.camera.stream) {
    for (const track of state.camera.stream.getTracks()) track.stop();
    state.camera.stream = null;
  }
  if (elements.cameraVideo) {
    try {
      elements.cameraVideo.pause();
    } catch {
      // ignore
    }
    elements.cameraVideo.srcObject = null;
  }
  if (elements.cameraSheet) elements.cameraSheet.hidden = true;
  if (elements.cameraCanvas) elements.cameraCanvas.hidden = true;
}

async function capturePhoto() {
  const video = elements.cameraVideo;
  if (!state.camera.active || !video || !video.videoWidth) {
    elements.cameraStatus.textContent = "La cámara todavía no está lista.";
    return;
  }
  const longest = Math.max(video.videoWidth, video.videoHeight);
  const scale = Math.min(1, 1280 / longest);
  const width = Math.round(video.videoWidth * scale);
  const height = Math.round(video.videoHeight * scale);
  const canvas = elements.cameraCanvas;
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  context.drawImage(video, 0, 0, width, height);

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.82));
  if (!blob) {
    elements.cameraStatus.textContent = "No pude generar la foto.";
    return;
  }
  if (blob.size > 2 * 1024 * 1024) {
    elements.cameraStatus.textContent = "La foto pesa demasiado. Probá otra vez.";
    return;
  }
  const token = state.pairing ? state.pairing.token : "";
  elements.cameraCapture.disabled = true;
  elements.cameraStatus.textContent = "Enviando foto…";
  try {
    const response = await fetch(`/api/photo?slot=${state.slot ?? 0}`, {
      method: "POST",
      headers: {
        "Content-Type": "image/jpeg",
        "X-Toxinator-Token": token,
      },
      body: blob,
    });
    if (!response.ok) {
      elements.cameraStatus.textContent =
        response.status === 401
          ? "Token inválido. Volvé a vincular el mando."
          : "La consola rechazó la foto.";
      return;
    }
    showToast("Foto enviada a la consola");
    haptic([18, 40, 18]);
    stopCamera();
  } catch {
    elements.cameraStatus.textContent = "No pude llegar a la consola.";
  } finally {
    elements.cameraCapture.disabled = false;
  }
}

function closeCamera() {
  stopCamera();
}

/* ---------- sheets ---------- */

function openSettings() {
  elements.settingsSheet.hidden = false;
  elements.settingsButton.classList.add("active");
  updateOrientation();
}

function closeSettings() {
  elements.settingsSheet.hidden = true;
  elements.settingsButton.classList.remove("active");
}

function updateCalibration(neutral) {
  state.neutral = [...neutral];
  updateReadout();
}

/* ---------- events ---------- */

if (elements.feedbackBanner) {
  elements.feedbackBanner.addEventListener("click", activateFeedback);
}
if (elements.settingsButton) {
  elements.settingsButton.addEventListener("click", openSettings);
}
if (elements.settingsClose) {
  elements.settingsClose.addEventListener("click", closeSettings);
}
if (elements.settingsSheet) {
  elements.settingsSheet.addEventListener("click", (event) => {
    if (event.target === elements.settingsSheet) closeSettings();
  });
}
if (elements.orientationLock) {
  elements.orientationLock.addEventListener("click", toggleOrientationLock);
}
if (elements.advancedButton) {
  elements.advancedButton.addEventListener("click", () => {
    applyAdvanced(!state.advanced, { persist: true });
    buzz(10);
  });
}
if (elements.panelToggle) {
  elements.panelToggle.addEventListener("click", () => {
    const expanded = elements.panel.classList.toggle("expanded");
    elements.panelToggle.setAttribute("aria-expanded", expanded ? "true" : "false");
  });
}

elements.scanButton.addEventListener("click", () => {
  if (state.scanner.active) {
    stopScanner();
    setPairingStatus(
      state.pairing
        ? `Vinculado a ${state.pairing.host}. Escaneá otro QR o reconectá.`
        : "Escaneá el QR de la consola."
    );
    return;
  }
  startScanner();
});

elements.manualToggle.addEventListener("click", () => toggleManual(true));
elements.manualCancel.addEventListener("click", () => toggleManual(false));

elements.manualForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const pairing = parsePairing(elements.manualHost.value, elements.manualToken.value);
  if (pairing.error) {
    setPairingStatus(pairing.error, "error");
    return;
  }
  stopScanner();
  savePairing(pairing);
  toggleManual(false);
  elements.retryButton.hidden = false;
  elements.openConsole.hidden = false;
  elements.unpairButton.hidden = false;
  closeSocket();
  state.fatal = false;
  state.manualDisconnect = false;
  state.everConnected = false;
  state.attempts = 0;
  setPairingStatus(`Conectando a ${pairing.host}…`, "working");
  connect();
});

elements.openConsole.addEventListener("click", () => {
  if (!state.pairing) return;
  const link = document.createElement("a");
  link.href = pairingUrl(state.pairing);
  link.target = "_blank";
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  showToast("Aceptá el certificado y volvé a la app.");
});

elements.retryButton.addEventListener("click", () => {
  if (!state.pairing) return;
  closeSocket();
  stopScanner();
  state.fatal = false;
  state.manualDisconnect = false;
  state.attempts = 0;
  state.everConnected = false;
  toggleManual(false);
  setPairingStatus(`Conectando a ${state.pairing.host}…`, "working");
  connect();
});

elements.unpairButton.addEventListener("click", () => {
  closeSocket();
  stopScanner();
  clearPairing();
  fillManual();
  elements.retryButton.hidden = true;
  elements.openConsole.hidden = true;
  elements.unpairButton.hidden = true;
  toggleManual(false);
  setPairingStatus("Consola olvidada. Escaneá el QR para vincular otra.");
});

elements.pairButton.addEventListener("click", () => {
  state.manualDisconnect = true;
  closeSocket();
  stopScanner();
  state.connected = false;
  toggleManual(false);
  const target = state.pairing ? state.pairing.host : "la consola";
  showPairing(`Vinculado a ${target}. Escaneá otro QR o reconectá.`);
});

elements.calibrate.addEventListener("click", () => {
  if (!state.connected) {
    setStatus("Conectá primero", "warn");
    showToast("Conectá primero", "warn");
    return;
  }
  if (!state.sensorsOn) {
    setStatus("Activá los sensores", "warn");
    showToast("Activá los sensores", "warn");
    enableSensors();
    return;
  }
  updateCalibration(state.orientation);
  send({ type: "calibrate" });
  setStatus("Calibrando…", "warn");
  showToast("Calibrando… mantené quieto");

  if (state.calibrationTimer !== null) window.clearTimeout(state.calibrationTimer);
  state.calibrationTimer = window.setTimeout(() => {
    state.calibrationTimer = null;
    if (state.connected) {
      setStatus("Sin respuesta", "warn");
      showToast("Sin respuesta de la consola", "error");
    }
  }, 2000);
});

elements.enableSensors.addEventListener("click", () => {
  enableSensors();
});

if (elements.sensors) {
  elements.sensors.addEventListener("click", () => {
    if (!state.sensorsOn) enableSensors();
  });
}

if (elements.cameraButton) {
  elements.cameraButton.addEventListener("click", openCamera);
}
if (elements.cameraCapture) {
  elements.cameraCapture.addEventListener("click", capturePhoto);
}
if (elements.cameraCancel) {
  elements.cameraCancel.addEventListener("click", closeCamera);
}
if (elements.cameraSheet) {
  elements.cameraSheet.addEventListener("click", (event) => {
    if (event.target === elements.cameraSheet) closeCamera();
  });
}

portraitQuery.addEventListener("change", updateOrientation);

for (const button of elements.installButtons) {
  button.addEventListener("click", promptInstall);
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) return;
  stopAudio();
  if (state.scanner.active) {
    stopScanner();
    setPairingStatus("Escaneo en pausa. Tocá ESCANEAR QR para volver.");
  }
  if (state.camera.active) stopCamera();
});

document.addEventListener("pointerdown", unlockAudio, { once: true });
document.addEventListener("pointerdown", autoEnableSensors, true);

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  state.deferredPrompt = event;
  updateInstallButtons();
});

window.addEventListener("appinstalled", () => {
  state.deferredPrompt = null;
  state.installed = true;
  updateInstallButtons();
  showToast("Mando instalado");
});

window.addEventListener("load", registerServiceWorker);

function sendLoop(now) {
  if (
    state.ws &&
    state.ws.readyState === WebSocket.OPEN &&
    state.connected &&
    now - state.lastSent >= 1000 / 60
  ) {
    state.lastSent = now;
    send({
      type: "state",
      t: now / 1000,
      accel: state.accel.map((value) => round(value, 2)),
      gyro: state.gyro.map((value) => round(value, 2)),
      orientation: state.orientation.map((value) => round(value, 1)),
      buttons: Array.from(state.buttons),
      move: state.move,
      touch: state.touch,
    });
  }
  window.requestAnimationFrame(sendLoop);
}

window.setInterval(() => {
  if (state.connected) send({ type: "ping", t: performance.now() });
}, 3000);

function init() {
  state.advanced = loadAdvanced();
  state.orientationLock = loadOrientationLock();
  applyAdvanced(state.advanced);
  applyController(null);
  updateFeedbackBanner();
  updateReadout();
  updateInstallButtons();
  updatePairingMode();
  updateOrientation();
  let stored = loadPairing();
  let initialError = "";

  if (queryToken) {
    const fromQuery = parsePairing(window.location.href, queryToken);
    if (!fromQuery.error) {
      stored = fromQuery;
      savePairing(fromQuery);
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, "", window.location.pathname + window.location.hash);
      }
    } else {
      initialError = fromQuery.error;
    }
  }

  if (stored) {
    state.pairing = stored;
    elements.retryButton.hidden = false;
    elements.openConsole.hidden = false;
    elements.unpairButton.hidden = false;
    elements.retryButton.textContent = "RECONECTAR";
    setPairingStatus(`Vinculado a ${stored.host}. Conectando…`, "working");
    connect();
  } else {
    const emptyMessage = secureContext()
      ? "Sin consola vinculada. Escaneá el QR de la consola."
      : "Modo HTTP: escaneá el QR con la cámara del teléfono y abrí el enlace, o ingresá IP y token.";
    showPairing(initialError || emptyMessage);
  }
}

init();
window.requestAnimationFrame(sendLoop);
