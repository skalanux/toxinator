"use strict";

const params = new URLSearchParams(window.location.search);
const token = params.get("token") || "";

const elements = {
  status: document.getElementById("status"),
  beta: document.getElementById("beta"),
  gamma: document.getElementById("gamma"),
  accel: document.getElementById("accel"),
  rtt: document.getElementById("rtt"),
  slot: document.getElementById("slot"),
  touchpad: document.getElementById("touchpad"),
  touchHint: document.getElementById("touch-hint"),
  stick: document.getElementById("stick"),
  aButton: document.getElementById("a-button"),
  calibrate: document.getElementById("calibrate"),
  enableSensors: document.getElementById("enable-sensors"),
};

const state = {
  ws: null,
  connected: false,
  fatal: false,
  slot: null,
  controllerId: "",
  orientation: [0, 0, 0],
  accel: [0, 0, 0],
  gyro: [0, 0, 0],
  touch: [],
  buttons: new Set(),
  sensorsOn: false,
  lastSent: 0,
  rtt: null,
  reconnectTimer: null,
};

function round(value, digits) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function setStatus(text, kind) {
  elements.status.textContent = text;
  elements.status.classList.remove("online", "offline", "warn");
  if (kind) elements.status.classList.add(kind);
}

function setSlot(text) {
  elements.slot.textContent = text;
}

function secure() {
  return window.isSecureContext && window.location.protocol === "https:";
}

function updateReadout() {
  const beta = state.orientation[1] || 0;
  const gamma = state.orientation[2] || 0;
  const magnitude = Math.hypot(state.accel[0], state.accel[1], state.accel[2]);
  elements.beta.textContent = `${beta.toFixed(0)}°`;
  elements.gamma.textContent = `${gamma.toFixed(0)}°`;
  elements.accel.textContent = magnitude.toFixed(1);
  elements.rtt.textContent = state.rtt === null ? "—" : `${Math.round(state.rtt)} ms`;
}

function send(message) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(message));
  }
}

function connect() {
  if (!secure()) {
    setStatus("Abrí por HTTPS", "offline");
    return;
  }
  if (!token) {
    setStatus("Abrí el QR", "offline");
    return;
  }
  if (state.ws && state.ws.readyState <= WebSocket.OPEN) return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
  state.ws = ws;
  setStatus("Conectando…", "warn");

  ws.addEventListener("open", () => {
    ws.send(
      JSON.stringify({
        type: "hello",
        token,
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
      state.connected = true;
      state.fatal = false;
      state.slot = message.slot;
      state.controllerId = message.controller_id || "";
      setStatus(`P${message.slot + 1} conectado`, "online");
      setSlot(`P${message.slot + 1} · ${state.controllerId}`);
      startSensorsIfPossible();
    } else if (message.type === "error") {
      state.fatal = true;
      if (message.code === "full") setStatus("Consola llena", "offline");
      else if (message.code === "bad-token") setStatus("Token inválido", "offline");
      else setStatus("Error de conexión", "offline");
      ws.close();
    } else if (message.type === "pong") {
      if (typeof message.t === "number") {
        state.rtt = Math.max(0, performance.now() - message.t);
        updateReadout();
      }
    } else if (message.type === "calibrated") {
      setStatus("Calibrado", "online");
      window.setTimeout(() => {
        if (state.connected) setStatus(`P${state.slot + 1} conectado`, "online");
      }, 900);
    }
  });

  ws.addEventListener("close", () => {
    const wasConnected = state.connected;
    state.connected = false;
    if (state.fatal) {
      setStatus("Sin conexión", "offline");
      return;
    }
    setStatus(wasConnected ? "Reconectando…" : "Buscando consola…", "warn");
    if (state.reconnectTimer === null) {
      state.reconnectTimer = window.setTimeout(() => {
        state.reconnectTimer = null;
        connect();
      }, 1200);
    }
  });

  ws.addEventListener("error", () => {
    ws.close();
  });
}

function startSensors() {
  if (state.sensorsOn) return;
  state.sensorsOn = true;
  elements.enableSensors.classList.add("hidden");

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
        return;
      }
    }
    startSensors();
  } catch {
    setStatus("Sensores bloqueados", "warn");
  }
}

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
  if (navigator.vibrate) navigator.vibrate(12);
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
  if (!state.connected) return;
  send({ type: "calibrate" });
  setStatus("Calibrando…", "warn");
});

elements.enableSensors.addEventListener("click", () => {
  enableSensors();
});

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

if (!token) {
  setStatus("Abrí el QR", "offline");
  setSlot("SIN TOKEN");
} else if (!secure()) {
  setStatus("Abrí por HTTPS", "offline");
} else {
  connect();
}

updateReadout();
window.requestAnimationFrame(sendLoop);
