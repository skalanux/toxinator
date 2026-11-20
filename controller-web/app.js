"use strict";

const STORAGE_KEY = "toxinator.pairing.v1";
const SKIN_KEY = "toxinator.skin.v1";
const ADVANCED_KEY = "toxinator.advanced.v1";
const params = new URLSearchParams(window.location.search);
const queryToken = (params.get("token") || "").trim();

const SKINS = [
  {
    id: "tokyo-night",
    name: "Tokyo Night",
    short: "Night",
    bg: "#1a1b26",
    accent: "#7aa2f7",
    status: "#9ece6a",
  },
  {
    id: "tokyo-storm",
    name: "Tokyo Storm",
    short: "Storm",
    bg: "#24283b",
    accent: "#bb9af7",
    status: "#7dcfff",
  },
  {
    id: "tokyo-moon",
    name: "Tokyo Moon",
    short: "Moon",
    bg: "#222436",
    accent: "#82aaff",
    status: "#c3e88d",
  },
  {
    id: "tokyo-mint",
    name: "Tokyo Mint",
    short: "Mint",
    bg: "#1a1b26",
    accent: "#73daca",
    status: "#9ece6a",
  },
];
const LAYOUTS = ["default", "motion", "touch"];
const DEFAULT_CONTROLLER = {
  layout: "default",
  skin: "tokyo-night",
  action: "Acción",
  back: "Volver",
  hint: "",
  game: "",
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
  status: document.getElementById("status"),
  beta: document.getElementById("beta"),
  gamma: document.getElementById("gamma"),
  accel: document.getElementById("accel"),
  rtt: document.getElementById("rtt"),
  slot: document.getElementById("slot"),
  sensors: document.getElementById("sensors"),
  touchpad: document.getElementById("touchpad"),
  touchHint: document.getElementById("touch-hint"),
  stick: document.getElementById("stick"),
  aButton: document.getElementById("a-button"),
  bButton: document.getElementById("b-button"),
  bLabel: document.getElementById("b-label"),
  calibrate: document.getElementById("calibrate"),
  enableSensors: document.getElementById("enable-sensors"),
  toast: document.getElementById("toast"),
  mode: document.getElementById("mode"),
  brandSubtitle: document.getElementById("brand-subtitle"),
  aLabel: document.getElementById("a-label"),
  footHint: document.getElementById("foot-hint"),
  skinButton: document.getElementById("skin-button"),
  advancedButton: document.getElementById("advanced-button"),
  skinSheet: document.getElementById("skin-sheet"),
  skinList: document.getElementById("skin-list"),
  skinClose: document.getElementById("skin-close"),
  feedbackBanner: document.getElementById("feedback-banner"),
  feedbackTitle: document.getElementById("feedback-title"),
  feedbackCopy: document.getElementById("feedback-copy"),
};

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
  touch: [],
  buttons: new Set(),
  sensorsOn: false,
  mode: "launcher",
  controller: { ...DEFAULT_CONTROLLER },
  skin: DEFAULT_CONTROLLER.skin,
  skinOverride: null,
  advanced: false,
  feedbackReady: false,
  lastSent: 0,
  rtt: null,
  welcomeTimer: null,
  reconnectTimer: null,
  calibrationTimer: null,
  toastTimer: null,
  bReleaseTimer: null,
  deferredPrompt: null,
  installed: false,
  scanner: {
    active: false,
    stream: null,
    lastScan: 0,
  },
};

function round(value, digits) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

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
  if (!elements.touchpad) return;
  elements.touchpad.classList.remove("feedback-pulse");
  void elements.touchpad.offsetWidth;
  elements.touchpad.classList.add("feedback-pulse");
  if (feedbackPulseTimer !== null) window.clearTimeout(feedbackPulseTimer);
  feedbackPulseTimer = window.setTimeout(() => {
    feedbackPulseTimer = null;
    elements.touchpad.classList.remove("feedback-pulse");
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

function updateFeedbackBanner() {
  if (!elements.feedbackBanner) return;
  const hint = feedbackHint();
  if (elements.feedbackTitle) elements.feedbackTitle.textContent = hint.title;
  if (elements.feedbackCopy) elements.feedbackCopy.textContent = hint.copy;
  elements.feedbackBanner.hidden =
    state.screen !== "controller" || state.mode === "launcher" || state.feedbackReady;
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

function activateFeedback() {
  unlockAudio();
  const hint = feedbackHint();
  const audio = Boolean(ensureAudio());
  const vibrated = hint.vibration ? haptic([250, 100, 400]) : false;
  if (audio) {
    playTone(660, 110, 0.35);
    window.setTimeout(() => playTone(880, 150, 0.30), 140);
  }
  state.feedbackReady = true;
  updateFeedbackBanner();
  if (!audio && !hint.vibration) {
    showToast("Este navegador no permite sonido ni vibración", "warn", 4200);
  } else if (!audio) {
    showToast("Vibración activada · audio no disponible", "warn", 4200);
  } else if (hint.ios) {
    showToast(
      "Audio activado · iPhone no permite vibrar desde la web",
      "warn",
      6000,
    );
  } else if (hint.firefox) {
    showToast(
      "Audio activado · Firefox Android no vibra; abrí el QR en Chrome",
      "warn",
      6000,
    );
  } else if (!hint.vibration) {
    showToast(
      "Audio activado · este navegador no expone vibración",
      "warn",
      6000,
    );
  } else if (vibrated === false) {
    showToast("Audio activado · el navegador no dejó vibrar", "warn", 4200);
  } else {
    showToast("Sonido y vibración activados");
  }
}

function setStatus(text, kind) {
  elements.status.textContent = text;
  elements.status.classList.remove("online", "offline", "warn");
  if (kind) elements.status.classList.add(kind);
}

function setSlot(text) {
  state.slotText = text;
  renderSlot();
}

function renderSlot() {
  const compact = state.slotText.split(" · ")[0];
  elements.slot.textContent = state.advanced ? state.slotText : compact;
}

function setPairingStatus(text, kind = "") {
  elements.pairingStatus.textContent = text;
  elements.pairingStatus.classList.remove("warn", "error", "working");
  if (kind) elements.pairingStatus.classList.add(kind);
}

function applyMode(mode) {
  state.mode = mode === "game" ? "game" : "launcher";
  if (state.mode === "launcher") stopAudio();
  updateFeedbackBanner();
  if (state.screen !== "controller") return;
  const launcher = state.mode === "launcher";
  document.body.classList.toggle("mode-launcher", launcher);
  document.body.classList.toggle("mode-game", !launcher);
  elements.mode.textContent = launcher ? "LAUNCHER" : "JUEGO";
  renderControllerChrome();
  if (!launcher && state.connected) startSensorsIfPossible();
}

function skinById(skinId) {
  return SKINS.find((skin) => skin.id === skinId) || SKINS[0];
}

function loadSkinOverride() {
  try {
    const stored = window.localStorage.getItem(SKIN_KEY);
    return SKINS.some((skin) => skin.id === stored) ? stored : null;
  } catch {
    return null;
  }
}

function saveSkinOverride(skinId) {
  try {
    if (skinId) window.localStorage.setItem(SKIN_KEY, skinId);
    else window.localStorage.removeItem(SKIN_KEY);
  } catch {
    // private mode: the skin still applies for this session
  }
}

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
    // private mode: the setting still applies for this session
  }
}

function applyAdvanced(enabled, { persist = false } = {}) {
  state.advanced = Boolean(enabled);
  document.body.classList.toggle("advanced", state.advanced);
  if (elements.advancedButton) {
    elements.advancedButton.textContent = state.advanced ? "Simple" : "Avanzado";
    elements.advancedButton.classList.toggle("active", state.advanced);
  }
  renderSlot();
  if (persist) saveAdvanced(state.advanced);
}

function applySkin(skinId, { persist = false } = {}) {
  const skin = skinById(skinId);
  state.skin = skin.id;
  document.body.dataset.skin = skin.id;
  if (elements.skinButton) {
    elements.skinButton.textContent = `Skin · ${skin.short}`;
  }
  if (persist) {
    state.skinOverride = skin.id;
    saveSkinOverride(skin.id);
  }
  renderSkinSheet();
}

function renderSkinSheet() {
  if (!elements.skinList) return;
  const current = state.skinOverride || state.skin;
  elements.skinList.textContent = "";
  for (const skin of SKINS) {
    const option = document.createElement("button");
    option.type = "button";
    option.className = "skin-option";
    option.classList.toggle("active", skin.id === current);
    option.setAttribute("aria-pressed", skin.id === current ? "true" : "false");

    const swatch = document.createElement("span");
    swatch.className = "skin-swatch";
    swatch.style.background =
      `linear-gradient(135deg, ${skin.bg}, ${skin.accent} 62%, ${skin.status})`;

    const copy = document.createElement("span");
    copy.className = "skin-copy";
    const name = document.createElement("strong");
    name.textContent = skin.name;
    const meta = document.createElement("small");
    meta.textContent = skin.id === current ? "ACTIVA" : "TOCAR PARA USAR";
    copy.append(name, meta);
    option.append(swatch, copy);

    option.addEventListener("click", () => {
      applySkin(skin.id, { persist: true });
      buzz(10);
      showToast(`Skin: ${skin.name}`);
    });
    elements.skinList.append(option);
  }
}

function openSkinSheet() {
  if (!elements.skinSheet) return;
  renderSkinSheet();
  elements.skinSheet.hidden = false;
  document.body.classList.add("sheet-open");
}

function closeSkinSheet() {
  if (!elements.skinSheet) return;
  elements.skinSheet.hidden = true;
  document.body.classList.remove("sheet-open");
}

function layoutHint(layout) {
  if (layout === "motion") return "Incliná el teléfono o arrastrá acá";
  if (layout === "touch") return "Arrastrá para apuntar";
  return "Incliná el teléfono o arrastrá acá";
}

function layoutFoot(layout) {
  if (layout === "motion") return "MOVIMIENTO · TOUCH OPCIONAL";
  if (layout === "touch") return "TOUCH · A ACCIÓN";
  return "MISMA WI-FI · CERTIFICADO ACEPTADO";
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
  elements.aLabel.textContent = launcher ? "ELEGIR" : controller.action;
  elements.bLabel.textContent = launcher ? "ATRÁS" : controller.back;
  if (launcher) {
    elements.touchHint.innerHTML = "Arrastrá para mover<br>y soltá al centro";
    elements.footHint.textContent = "ARRASTRÁ · A ELEGIR";
  } else {
    elements.touchHint.textContent = controller.hint || layoutHint(controller.layout);
    elements.footHint.textContent = controller.hint || layoutFoot(controller.layout);
  }
}

function applyController(profile) {
  const source = profile && typeof profile === "object" ? profile : {};
  const layout = LAYOUTS.includes(source.layout) ? source.layout : DEFAULT_CONTROLLER.layout;
  const skin = SKINS.some((item) => item.id === source.skin)
    ? source.skin
    : DEFAULT_CONTROLLER.skin;
  state.controller = {
    layout,
    skin,
    action:
      typeof source.action === "string" && source.action.trim()
        ? source.action.trim().slice(0, 24)
        : DEFAULT_CONTROLLER.action,
    back:
      typeof source.back === "string" && source.back.trim()
        ? source.back.trim().slice(0, 24)
        : DEFAULT_CONTROLLER.back,
    hint: typeof source.hint === "string" ? source.hint.trim().slice(0, 80) : "",
    game: typeof source.game === "string" ? source.game.slice(0, 60) : "",
  };
  document.body.dataset.layout = state.controller.layout;
  applySkin(state.skinOverride || state.controller.skin);
  renderControllerChrome();
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
    // private mode or quota; pairing still works for this session
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

function updateReadout() {
  const beta = (state.orientation[1] || 0) - (state.neutral[1] || 0);
  const gamma = (state.orientation[2] || 0) - (state.neutral[2] || 0);
  const magnitude = Math.hypot(state.accel[0], state.accel[1], state.accel[2]);
  elements.beta.textContent = `${beta.toFixed(0)}°`;
  elements.gamma.textContent = `${gamma.toFixed(0)}°`;
  elements.accel.textContent = magnitude.toFixed(1);
  elements.rtt.textContent = state.rtt === null ? "—" : `${Math.round(state.rtt)} ms`;
  elements.sensors.textContent = state.sensorsOn ? "SENSORES ON" : "SENSORES OFF";
  elements.sensors.classList.toggle("on", state.sensorsOn);
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
  if (state.bReleaseTimer !== null) {
    window.clearTimeout(state.bReleaseTimer);
    state.bReleaseTimer = null;
  }
  state.touch = [];
  touchPointer = null;
  touchOrigin = null;
  elements.aButton.classList.remove("pressed");
  elements.bButton.classList.remove("pressed");
  elements.stick.style.left = "50%";
  elements.stick.style.top = "50%";
}

function closeSocket() {
  clearReconnect();
  stopAudio();
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
      buzz(18);
    } else if (message.type === "mode") {
      applyMode(message.mode);
    } else if (message.type === "controller") {
      applyController(message.profile);
    } else if (message.type === "haptic" || message.type === "audio") {
      applyFeedback(message);
    } else if (message.type === "error") {
      state.fatal = true;
      let text = "Error de conexión.";
      if (message.code === "full") {
        text = "La consola ya tiene 4 mandos conectados.";
      } else if (message.code === "bad-token") {
        text = "Token inválido. Escaneá el QR de la consola otra vez.";
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
  if (!needsPermission()) {
    startSensors();
  } else {
    elements.enableSensors.classList.remove("hidden");
  }
}

async function enableSensors() {
  try {
    if (needsPermission()) {
      const result = await window.DeviceMotionEvent.requestPermission();
      if (result !== "granted") {
        setStatus("Sensores bloqueados", "warn");
        showToast("Sensores bloqueados", "error");
        return;
      }
    }
    startSensors();
  } catch {
    setStatus("Sensores bloqueados", "warn");
    showToast("No pude activar los sensores", "error");
  }
}

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

elements.touchpad.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  touchPointer = event.pointerId;
  touchOrigin = { x: event.clientX, y: event.clientY };
  elements.touchpad.setPointerCapture(event.pointerId);
  elements.touchHint.classList.add("hidden");
  if (state.mode === "launcher") {
    state.touch = [{ id: 0, x: 0.5, y: 0.5, pressure: 1 }];
    elements.stick.style.left = "50%";
    elements.stick.style.top = "50%";
    return;
  }
  updateTouch(event);
});

elements.touchpad.addEventListener("pointermove", (event) => {
  if (event.pointerId !== touchPointer) return;
  event.preventDefault();
  if (state.mode === "launcher") updateLauncherStick(event);
  else updateTouch(event);
});

function updateTouch(event) {
  const rect = elements.touchpad.getBoundingClientRect();
  const x = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  const y = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
  state.touch = [{ id: 0, x, y, pressure: 1 }];
  elements.stick.style.left = `${x * 100}%`;
  elements.stick.style.top = `${y * 100}%`;
  elements.touchHint.classList.add("hidden");
}

const LAUNCHER_STICK_RADIUS = 0.36;
const LAUNCHER_STICK_GAIN = 2.1;

function updateLauncherStick(event) {
  if (!touchOrigin) return;
  const rect = elements.touchpad.getBoundingClientRect();
  let dx = ((event.clientX - touchOrigin.x) / rect.width) * LAUNCHER_STICK_GAIN;
  let dy = ((event.clientY - touchOrigin.y) / rect.height) * LAUNCHER_STICK_GAIN;
  const distance = Math.hypot(dx, dy);
  if (distance > LAUNCHER_STICK_RADIUS) {
    const scale = LAUNCHER_STICK_RADIUS / distance;
    dx *= scale;
    dy *= scale;
  }
  const x = 0.5 + dx;
  const y = 0.5 + dy;
  state.touch = [{ id: 0, x, y, pressure: 1 }];
  elements.stick.style.left = `${x * 100}%`;
  elements.stick.style.top = `${y * 100}%`;
}

let touchPointer = null;
let touchOrigin = null;

function endTouch(event) {
  if (event.pointerId !== touchPointer) return;
  touchPointer = null;
  touchOrigin = null;
  state.touch = [];
  elements.stick.style.left = "50%";
  elements.stick.style.top = "50%";
}

elements.touchpad.addEventListener("pointerup", endTouch);
elements.touchpad.addEventListener("pointercancel", endTouch);

elements.aButton.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  state.buttons.add("A");
  elements.aButton.classList.add("pressed");
  buzz(12);
});

function releaseA(event) {
  event.preventDefault();
  state.buttons.delete("A");
  elements.aButton.classList.remove("pressed");
}

elements.aButton.addEventListener("pointerup", releaseA);
elements.aButton.addEventListener("pointercancel", releaseA);
elements.aButton.addEventListener("pointerleave", releaseA);
elements.aButton.addEventListener("contextmenu", (event) => event.preventDefault());

elements.bButton.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  if (state.bReleaseTimer !== null) {
    window.clearTimeout(state.bReleaseTimer);
    state.bReleaseTimer = null;
  }
  state.buttons.add("B");
  elements.bButton.classList.add("pressed");
  buzz(12);
});

function releaseB(event) {
  event.preventDefault();
  elements.bButton.classList.remove("pressed");
  if (state.bReleaseTimer !== null) window.clearTimeout(state.bReleaseTimer);
  state.bReleaseTimer = window.setTimeout(() => {
    state.bReleaseTimer = null;
    state.buttons.delete("B");
  }, 150);
}

elements.bButton.addEventListener("pointerup", releaseB);
elements.bButton.addEventListener("pointercancel", releaseB);
elements.bButton.addEventListener("pointerleave", releaseB);
elements.bButton.addEventListener("contextmenu", (event) => event.preventDefault());

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

  state.neutral = [...state.orientation];
  updateReadout();
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

if (elements.skinButton) {
  elements.skinButton.addEventListener("click", () => {
    openSkinSheet();
    buzz(10);
  });
}

if (elements.advancedButton) {
  elements.advancedButton.addEventListener("click", () => {
    applyAdvanced(!state.advanced, { persist: true });
    buzz(10);
    showToast(state.advanced ? "Modo avanzado" : "Mando simple");
  });
}

if (elements.skinClose) {
  elements.skinClose.addEventListener("click", closeSkinSheet);
}

if (elements.skinSheet) {
  elements.skinSheet.addEventListener("click", (event) => {
    if (event.target === elements.skinSheet) closeSkinSheet();
  });
}

if (elements.feedbackBanner) {
  elements.feedbackBanner.addEventListener("click", activateFeedback);
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

for (const button of elements.installButtons) {
  button.addEventListener("click", promptInstall);
}

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
      touch: state.touch,
    });
  }
  window.requestAnimationFrame(sendLoop);
}

window.setInterval(() => {
  if (state.connected) send({ type: "ping", t: performance.now() });
}, 3000);

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) return;
  stopAudio();
  if (!state.scanner.active) return;
  stopScanner();
  setPairingStatus("Escaneo en pausa. Tocá ESCANEAR QR para volver.");
});

document.addEventListener("pointerdown", unlockAudio, { once: true });

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

function init() {
  state.skinOverride = loadSkinOverride();
  applyController({});
  applyAdvanced(loadAdvanced());
  updateFeedbackBanner();
  updateReadout();
  updateInstallButtons();
  updatePairingMode();
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
