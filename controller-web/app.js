"use strict";

const STORAGE_KEY = "toxinator.pairing.v1";
const params = new URLSearchParams(window.location.search);
const queryToken = (params.get("token") || "").trim();

const elements = {
  pairing: document.getElementById("pairing"),
  controller: document.getElementById("controller"),
  installButtons: [
    document.getElementById("install-button"),
    document.getElementById("install-button-2"),
  ].filter(Boolean),
  pairingStatus: document.getElementById("pairing-status"),
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
  calibrate: document.getElementById("calibrate"),
  enableSensors: document.getElementById("enable-sensors"),
  toast: document.getElementById("toast"),
  mode: document.getElementById("mode"),
  aLabel: document.getElementById("a-label"),
  footHint: document.getElementById("foot-hint"),
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
  controllerId: "",
  orientation: [0, 0, 0],
  neutral: [0, 0, 0],
  accel: [0, 0, 0],
  gyro: [0, 0, 0],
  touch: [],
  buttons: new Set(),
  sensorsOn: false,
  mode: "launcher",
  lastSent: 0,
  rtt: null,
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
};

function round(value, digits) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function buzz(milliseconds) {
  if (navigator.vibrate) navigator.vibrate(milliseconds);
}

function setStatus(text, kind) {
  elements.status.textContent = text;
  elements.status.classList.remove("online", "offline", "warn");
  if (kind) elements.status.classList.add(kind);
}

function setSlot(text) {
  elements.slot.textContent = text;
}

function setPairingStatus(text, kind = "") {
  elements.pairingStatus.textContent = text;
  elements.pairingStatus.classList.remove("warn", "error", "working");
  if (kind) elements.pairingStatus.classList.add(kind);
}

function applyMode(mode) {
  state.mode = mode === "game" ? "game" : "launcher";
  if (state.screen !== "controller") return;
  const launcher = state.mode === "launcher";
  document.body.classList.toggle("mode-launcher", launcher);
  document.body.classList.toggle("mode-game", !launcher);
  elements.mode.textContent = launcher ? "LAUNCHER" : "JUEGO";
  elements.aLabel.textContent = launcher ? "ELEGIR" : "ACCIÓN";
  elements.touchHint.innerHTML = launcher
    ? "Arrastrá para mover<br>y soltá en el centro"
    : "Incliná el teléfono<br>o arrastrá acá";
  elements.footHint.textContent = launcher
    ? "JOYSTICK · A ELEGIR"
    : "Misma Wi-Fi · certificado aceptado";
  if (!launcher && state.connected) startSensorsIfPossible();
}

function showToast(message, kind = "") {
  elements.toast.textContent = message;
  elements.toast.classList.remove("warn", "error");
  if (kind) elements.toast.classList.add(kind);
  elements.toast.classList.add("show");
  if (state.toastTimer !== null) window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => {
    state.toastTimer = null;
    elements.toast.classList.remove("show");
  }, 1900);
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

function parsePairing(text, tokenFallback = "") {
  const value = String(text || "").trim();
  if (!value) {
    return { error: "Ingresá la IP o la URL de la consola." };
  }
  const hasScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(value);
  const candidate = hasScheme ? value : `https://${value}`;
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
  state.screen = "pairing";
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
  } else {
    setPairingStatus(
      `No pude llegar a ${target}. Revisá la Wi-Fi y el firewall. ` +
        `Si cambió la IP, escaneá el QR nuevo. Si es la primera vez, ` +
        `abrí ${pairingUrl(pairing)} en el navegador y aceptá el certificado.`,
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
  state.touch = [];
  touchPointer = null;
  elements.aButton.classList.remove("pressed");
  elements.stick.style.left = "50%";
  elements.stick.style.top = "50%";
}

function closeSocket() {
  clearReconnect();
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
      `La consola está en HTTP. Abrí https://${state.pairing.host}/ una vez y aceptá el certificado.`,
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
      "La cámara necesita HTTPS. Abrí la URL de la consola y aceptá el certificado.",
      "error"
    );
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
  elements.touchpad.setPointerCapture(event.pointerId);
  updateTouch(event);
});

elements.touchpad.addEventListener("pointermove", (event) => {
  if (event.pointerId !== touchPointer) return;
  event.preventDefault();
  updateTouch(event);
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

let touchPointer = null;

function endTouch(event) {
  if (event.pointerId !== touchPointer) return;
  touchPointer = null;
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
  if (!document.hidden || !state.scanner.active) return;
  stopScanner();
  setPairingStatus("Escaneo en pausa. Tocá ESCANEAR QR para volver.");
});

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
  updateReadout();
  updateInstallButtons();
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
    showPairing(initialError || "Sin consola vinculada. Escaneá el QR de la consola.");
  }
}

init();
window.requestAnimationFrame(sendLoop);
