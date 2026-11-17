"use strict";

const overlay = document.getElementById("overlay");
const overlayStatus = document.getElementById("overlay-status");
const startButton = document.getElementById("start");
const statusElement = document.getElementById("status");
const accelElement = document.getElementById("accel");
const gyroElement = document.getElementById("gyro");
const orientationElement = document.getElementById("orientation");
const throwButton = document.getElementById("throw");
const calibrateButton = document.getElementById("calibrate");

const token = new URLSearchParams(window.location.search).get("token") || "";
const GRAVITY = 9.80665;

let socket = null;
let started = false;
let throwHeld = false;
let sequence = 0;
let accel = [0, 0, 0];
let gyro = [0, 0, 0];
let euler = { alpha: 0, beta: 0, gamma: 0 };
let neutral = null;

function setStatus(text) {
  statusElement.textContent = text;
  overlayStatus.textContent = text;
}

function format(value, digits = 2) {
  return Number.isFinite(value) ? value.toFixed(digits) : "—";
}

function updateReadout() {
  accelElement.textContent = `${format(accel[0])} ${format(accel[1])} ${format(accel[2])} g`;
  gyroElement.textContent = `${format(gyro[0], 0)} ${format(gyro[1], 0)} ${format(gyro[2], 0)} °/s`;
  orientationElement.textContent = `${format(euler.alpha, 0)} ${format(euler.beta, 0)} ${format(euler.gamma, 0)}°`;
}

function wrapDegrees(value) {
  return ((value + 180) % 360 + 360) % 360 - 180;
}

function relativeEuler() {
  if (neutral === null) {
    return { ...euler };
  }
  return {
    alpha: wrapDegrees(euler.alpha - neutral.alpha),
    beta: wrapDegrees(euler.beta - neutral.beta),
    gamma: wrapDegrees(euler.gamma - neutral.gamma),
  };
}

function eulerToQuat(alphaDeg, betaDeg, gammaDeg) {
  const alpha = (alphaDeg * Math.PI) / 180 / 2;
  const beta = (betaDeg * Math.PI) / 180 / 2;
  const gamma = (gammaDeg * Math.PI) / 180 / 2;

  const cA = Math.cos(alpha);
  const sA = Math.sin(alpha);
  const cB = Math.cos(beta);
  const sB = Math.sin(beta);
  const cG = Math.cos(gamma);
  const sG = Math.sin(gamma);

  return [
    sA * cB * cG - cA * sB * sG,
    cA * sB * cG + sA * cB * sG,
    cA * cB * sG - sA * sB * cG,
    cA * cB * cG + sA * sB * sG,
  ];
}

function onMotion(event) {
  const acceleration = event.accelerationIncludingGravity || event.acceleration;
  if (acceleration) {
    accel = [
      (acceleration.x || 0) / GRAVITY,
      (acceleration.y || 0) / GRAVITY,
      (acceleration.z || 0) / GRAVITY,
    ];
  }
  if (event.rotationRate) {
    gyro = [
      event.rotationRate.alpha || 0,
      event.rotationRate.beta || 0,
      event.rotationRate.gamma || 0,
    ];
  }
  updateReadout();
}

function onOrientation(event) {
  euler = {
    alpha: event.alpha || 0,
    beta: event.beta || 0,
    gamma: event.gamma || 0,
  };
  updateReadout();
}

function sendState() {
  if (!started || socket === null || socket.readyState !== WebSocket.OPEN) {
    return;
  }
  const relative = relativeEuler();
  const quaternion = eulerToQuat(relative.alpha, relative.beta, relative.gamma);
  socket.send(
    JSON.stringify({
      type: "state",
      id: "phone",
      slot: 1,
      seq: sequence++ & 0xffff,
      accel,
      gyro,
      orientation: quaternion,
      orientation_euler: relative,
      buttons: { b: throwHeld },
      touches: [],
    })
  );
}

function connect() {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${scheme}://${window.location.host}/ws?token=${encodeURIComponent(token)}`;
  socket = new WebSocket(url);

  socket.addEventListener("open", () => {
    setStatus("Conectado");
    socket.send(JSON.stringify({ type: "hello", id: "phone", slot: 1 }));
  });

  socket.addEventListener("close", () => {
    setStatus("Desconectado");
    if (started) {
      window.setTimeout(connect, 1000);
    }
  });

  socket.addEventListener("error", () => {
    setStatus("Error de conexión");
  });
}

async function enableSensors() {
  if (!("DeviceMotionEvent" in window)) {
    throw new Error("Este navegador no expone sensores de movimiento");
  }

  if (typeof DeviceMotionEvent.requestPermission === "function") {
    const state = await DeviceMotionEvent.requestPermission();
    if (state !== "granted") {
      throw new Error("Permiso de movimiento denegado");
    }
  }

  if (
    typeof DeviceOrientationEvent !== "undefined" &&
    typeof DeviceOrientationEvent.requestPermission === "function"
  ) {
    try {
      await DeviceOrientationEvent.requestPermission();
    } catch {
      // Orientation is useful but not strictly required for the first test.
    }
  }

  window.addEventListener("devicemotion", onMotion, { passive: true });
  window.addEventListener("deviceorientation", onOrientation, { passive: true });
}

async function start() {
  if (!window.isSecureContext) {
    setStatus("Necesitás HTTPS o localhost para usar los sensores");
    return;
  }
  if (!token) {
    setStatus("Falta el token en la URL");
    return;
  }

  try {
    await enableSensors();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "No se pudieron habilitar los sensores");
    return;
  }

  started = true;
  overlay.classList.add("hidden");
  connect();
}

function throwDown(event) {
  if (event && typeof event.preventDefault === "function") {
    event.preventDefault();
  }
  if (throwHeld) {
    return;
  }
  throwHeld = true;
  throwButton.classList.add("active");
  sendState();
  if (navigator.vibrate) {
    navigator.vibrate(10);
  }
}

function throwUp(event) {
  if (event && typeof event.preventDefault === "function") {
    event.preventDefault();
  }
  if (!throwHeld) {
    return;
  }
  throwHeld = false;
  throwButton.classList.remove("active");
  sendState();
  if (navigator.vibrate) {
    navigator.vibrate([20, 30, 20]);
  }
}

startButton.addEventListener("click", start);

throwButton.addEventListener("pointerdown", (event) => {
  try {
    throwButton.setPointerCapture(event.pointerId);
  } catch {
    // Pointer capture is a nice-to-have.
  }
  throwDown(event);
});
throwButton.addEventListener("pointerup", throwUp);
throwButton.addEventListener("pointercancel", throwUp);
throwButton.addEventListener("lostpointercapture", throwUp);

calibrateButton.addEventListener("click", () => {
  neutral = { ...euler };
  setStatus("Pose neutra calibrada");
});

window.addEventListener("keydown", (event) => {
  if (event.code === "Space") {
    throwDown(event);
  }
});
window.addEventListener("keyup", (event) => {
  if (event.code === "Space") {
    throwUp(event);
  }
});

window.setInterval(sendState, 16);

if (!window.isSecureContext) {
  setStatus("Aviso: abrí por localhost (adb reverse) o HTTPS para sensores");
} else if (!token) {
  setStatus("Aviso: falta el token en la URL");
} else {
  setStatus("Listo para empezar");
}

updateReadout();
