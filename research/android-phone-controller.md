# Android phone as a LAN controller — research

**Ticket:** #4 · **Branch:** `research/android-phone-controller` · **Date:** 2026-11-16

**Question:** what is the best way to use an Android phone as a controller for a
personal Linux-first Python 3D game console over the LAN, from the browser?

**Assumptions from the project brief (not researched here):** the console is
Python, the phone sits next to a real Wii Remote, the first game is bowling
(swing + buttons + optional aim/spin), and a kart game (tilt/steer + buttons) is
planned. Target is 60 FPS and **input-to-game-state latency under 50 ms on LAN**.
No iOS requirement.

**Scope of this note:** Chrome for Android as the reference browser, Firefox for
Android as a secondary browser. It covers only what the browser can do on the
phone; the console-side game architecture is out of scope.

---

## 1. Bottom line

**The browser is sufficient for both bowling and kart at 60 FPS.** Build a small
installable PWA served **over HTTPS from the console itself**, use
`DeviceMotion` at 60 Hz for swing dynamics, `DeviceOrientation` for tilt/steer,
Pointer Events for touch, and one **WSS** connection carrying small binary
packets. Keep the design “latest state wins” rather than an event queue.

The hard part is **not** the controller code. It is getting a **trusted HTTPS
origin on the LAN**, because the sensor and PWA capabilities we need (sensors,
wake lock, service worker, installability) are gated on a secure context
`[S1][S4]`, and a page served from `http://192.168.x.x` is not one `[S4]`. Chrome’s Local Network Access rules add a second gate for
public→LAN WebSocket connections, but a page served from the console’s own LAN
origin is same-origin local→local and is not gated by the first LNA milestone
`[S13][S14][S16]`.

Recommended transport: **WebSocket over WSS**, not WebRTC. At 60 Hz and ~32
bytes per motion packet, bandwidth is ~2 KB/s per phone; WebRTC’s signalling,
ICE and DTLS machinery buys little on a healthy LAN. Keep WebRTC as a measured
fallback if Wi-Fi loss causes head-of-line stalls, not as the starting point
`[S17][S18][S20][S21]`.

---

## 2. The constraints that decide the design

### 2.1 Sensors require a secure context

`DeviceMotionEvent` and `DeviceOrientationEvent` are `[SecureContext]` APIs
`[S1]`; MDN states the same for both interfaces `[S2][S3]`. A secure context is
HTTPS or a loopback address such as `http://localhost` `[S4]`. A plain
`http://192.168.1.50:8080` page is **not** a secure context, even though it is
on the LAN `[S4]`. That single fact rules out the naive “Python HTTP server on
the LAN” approach for sensors, service workers and wake lock.

### 2.2 Chrome Local Network Access (LNA)

Chrome 142 restricted requests **from a public website to a local IP or
loopback**, gated behind a permission prompt and restricted to secure contexts
`[S13]`. Chrome 147 extended the same restriction to **WebSocket** and
WebTransport connections `[S14]`. The LNA specification defines a local network
request as a request whose target is *less public* than the initiator’s address
space, and its current implementation note says Chromium only enforces
**public→local** (not local→local) today `[S16]`.

Two practical consequences:

1. **Serve the controller page from the console’s LAN origin**
   (`https://console.local:8443` or `https://192.168.1.50:8443`). The page’s
   policy-container address space is then local, the WSS URL is the same origin,
   and the first LNA milestone does not apply. The spec’s check explicitly
   returns “no check” for a potentially trustworthy same-origin request `[S16]`.
2. **Do not serve the page from a public tunnel or public HTTPS host** and then
   connect to `wss://192.168.x.x`: that is public→local, and Chrome 147+ will
   prompt for local-network permission `[S14]`. It can work if the user grants
   it, but it adds a permission step and a dependency on the tunnel.

LNA is Chrome-specific. Firefox may behave differently; do not assume the same
prompt or the same exemptions.

### 2.3 `ws://` from an HTTPS page is blocked

An HTTPS page cannot open an insecure `ws://` WebSocket: it is blockable mixed
content `[S5]`. The LNA specification notes that WebSockets have **no
`targetAddressSpace` equivalent** to the `fetch()` mixed-content exemption, so
there is no supported way to bypass the mixed-content check for `ws://` `[S16]`.
Use `wss://` on the same origin as the page. This is also required for the token
not to travel in clear text.

### 2.4 Getting a trusted certificate on the LAN

There are four workable options; only the first two are recommended.

| Option | How it works | Trade-off |
|---|---|---|
| **Local CA (mkcert-style)** | Generate a local root CA, install it once on the phone via Android Settings, issue a leaf cert with SANs for `console.local` and/or the LAN IP. Chrome’s Android verifier explicitly loads **user-added roots** (`net::android::GetUserAddedRoots()`) `[S33]`. | One-time manual install per phone; Android’s CA-install UI varies by OEM; other browsers may not trust the same store. |
| **Public domain + Let’s Encrypt DNS-01** | Own a domain, point an A record at the console’s LAN IP, issue a normal Let’s Encrypt cert with DNS-01. DNS-01 works even when the web server is not reachable from the public internet `[S34]`. | Requires a domain and DNS API credentials; renewal automation; public DNS reveals a private A record (minor). No phone-side CA install. |
| **Let’s Encrypt IP certificate** | A cert whose SAN is the LAN IP. | IP certs must be short-lived and can only use HTTP-01 or TLS-ALPN-01; DNS-01 cannot validate an IP `[S34][S35]`. A LAN-only console is not reachable for those challenges, so this is impractical unless you temporarily expose it. |
| **Tunnel** (Cloudflare Tunnel, etc.) | Public HTTPS hostname tunnels to the console. | Adds an external dependency and usually routes gameplay traffic off-LAN; latency and availability become someone else’s problem. Acceptable as a fallback, not as the primary design. |

A local CA that Chrome trusts satisfies the HTTPS/secure-context gate; whether
Chrome shows the install promotion is a separate installability decision driven
by the criteria in §6.1 `[S27]`.

**Do not rely on clicking through a certificate warning.** It is poor UX, it
breaks the “installable PWA” story, and certificate errors are not a stable
platform contract. Install a trusted CA or use a publicly trusted certificate.

For development only, `adb reverse tcp:8443 tcp:8443` plus
`http://localhost:8443` gives a secure context without TLS, because `localhost`
is potentially trustworthy `[S4]`. That is not a shipping path: it needs USB/adb.

---

## 3. Sensors

### 3.1 API surface

`DeviceMotionEvent` provides:

- `acceleration` — linear acceleration without gravity, m/s² `[S1][S2]`
- `accelerationIncludingGravity` — proper acceleration including gravity, m/s² `[S1]`
- `rotationRate` — rotation rate in deg/s around the device axes `[S1]`
- `interval` — the interval at which data is obtained, in ms `[S1][S2]`

`DeviceOrientationEvent` provides `alpha`, `beta`, `gamma` in degrees and an
`absolute` flag `[S1]`. On Android Chrome the default `deviceorientation` event
is **relative**, not compass-absolute; Chrome changed to relative values in
Chrome 50 `[S3]`. Do not treat `alpha` as a compass heading.

The coordinate system is x right, y up, z out of the screen, defined relative to
the device’s natural orientation `[S1]`. Android’s sensor coordinate system is
also relative to the natural orientation and does **not** rotate when the screen
rotates `[S31]`. If the phone is held in landscape but its natural orientation
is portrait, the sensor axes are still portrait-relative; remap using
`screen.orientation.angle` or lock the game to the natural orientation.

### 3.2 Actual rates in Chrome

This is the most important implementation detail for the latency budget:

- Chrome’s device-sensor event pump runs at a fixed **60 Hz**
  (`kDefaultPumpFrequencyHz = 60`) `[S6]`.
- `devicemotion` fires from that pump every **16 ms**, and its `interval`
  property is reported as 16 ms `[S8]`.
- `deviceorientation` also uses the 60 Hz timer, but only dispatches when an
  angle differs from the previous one by more than **0.1°** in Chrome
  (`kOrientationThreshold = 0.1`) `[S7]`. The spec recommends a maximum
  threshold of 1° `[S1]`. So a stationary phone produces no orientation events,
  while a moving phone can approach 60 Hz.
- The Generic Sensor API does **not** give a higher rate in Chrome: motion
  sensor traits cap `frequency` at **60 Hz**, and the default is **10 Hz** if you
  do not set it `[S9]`. There is no Chrome path to 100/200 Hz.

**Design consequence:** use `devicemotion` for continuous dynamics (bowling
swing, spin, gesture detection) because it fires unconditionally at 60 Hz. Use
`deviceorientation` for slow tilt/steer where an event-driven absolute angle is
more convenient; holding the last value while stationary is correct for
steering. Do not build a 120 Hz controller in the browser; it is not available.

### 3.3 Permissions and the Chrome transition

Chromium’s permissions work added a tri-state (allow/ask/block) model, but as of
the March 2026 update the default was still **Allow** `[S12]`. Chrome 151 shipped
`DeviceMotionEvent.requestPermission()` and
`DeviceOrientationEvent.requestPermission()` `[S10]`, and Chrome’s stated plan is
to move the default to **Ask** eventually, at which point listeners will not
receive events until the page calls `requestPermission()` `[S11][S12]`.
**Verify the current default on the target Chrome**; the API is designed to work
on either side of the transition.

**Design consequence:** call `requestPermission()` defensively on the first user
tap if it exists, but do not require it. This works on both sides of the
transition:

```js
async function enableMotion() {
  if (typeof DeviceMotionEvent === "undefined") return false;
  if (typeof DeviceMotionEvent.requestPermission === "function") {
    try {
      const state = await DeviceMotionEvent.requestPermission();
      if (state !== "granted") return false;
    } catch {
      return false; // no transient activation, or user denied
    }
  }
  window.addEventListener("devicemotion", onMotion, { passive: true });
  return true;
}
```

Call it from a real tap (“Start controller”), not on page load: the spec rejects
when the permission state is `prompt` and there is no transient activation
`[S1]`. If it returns `denied`, fall back to touch-only controls and show a
short explanation.

Do not assume the API exists on every Android WebView or older Chrome. Feature
detect; the same code path handles Firefox, where `requestPermission` is not
implemented `[S38]`.

### 3.4 Firefox for Android

MDN’s compatibility data says Firefox for Android supports both
`DeviceMotionEvent` and `DeviceOrientationEvent` (mirroring desktop support)
`[S2][S3]`. It does **not** expose `requestPermission()` `[S38]`. Other
differences matter if Firefox is a supported target:

- `navigator.vibrate()` is present but **disabled** on Firefox for Android; it
  returns `true` without vibrating `[S36]`.
- `screen.orientation.lock()` only became functional in Firefox for Android 144;
  earlier versions had the API but returned `NS_ERROR_UNEXPECTED` `[S37]`.
- Screen Wake Lock is supported from Firefox 126 `[S39]`.

For this project, **Chrome for Android is the reference browser**; Firefox can
be a best-effort secondary target. The sensor path is the same, but do not rely
on vibration or early orientation lock there.

### 3.5 Sensor availability and quality

Android does not require manufacturers to include any particular sensor, and
motion-sensor availability varies `[S31]`. The accelerometer is nearly universal;
the gyroscope is common but not guaranteed. Chrome’s `devicemotion` pump starts
the accelerometer, linear-acceleration and gyroscope sensors together, and its
data object can contain `NaN` for a sensor that is unavailable `[S8]`. Check for
finite values and fall back to `deviceorientation` or touch if the gyro is
missing.

Native Android exposes calibrated and uncalibrated gyroscope, gravity, linear
acceleration and rotation-vector sensors `[S31]`. The browser’s
`deviceorientation` is a fused, high-level orientation; `devicemotion` gives you
the accelerometer/linear-acceleration/gyro components `[S1][S8]`. For a bowling
swing, the raw components are more useful than the fused angle; for kart
steering, the fused angle is more stable.

---

## 4. Touch: buttons, joystick, gestures, multitouch

Use **Pointer Events**, not mouse or click events. Pointer Events are the
standard DOM model for mouse, pen and touch, and every finger gets a
`pointerId`; `isPrimary`, `pointerType`, `setPointerCapture()` and
`pointercancel` are all defined `[S23]`.

Practical rules:

- **Press on `pointerdown`, release on `pointerup` and `pointercancel`.** Never
  use `click` for game buttons: it fires after release and is the wrong edge.
- **`touch-action: none`** on the game surface and controls, to stop the browser
  from turning a drag into a scroll/zoom and firing `pointercancel` `[S23]`.
- **Capture the pointer** with `setPointerCapture(pointerId)` so a finger that
  slides off a button still releases it correctly `[S23]`.
- **Track each finger by `pointerId`.** A virtual joystick and several buttons
  can be held simultaneously; do not use a single “current touch”.
- **Handle `pointercancel`** by releasing all state associated with that pointer.
  This happens when the browser takes over the gesture or the app loses focus
  `[S23]`.
- **Large targets.** MDN recommends targets large enough for the contact area;
  as a rule of thumb, thumb-sized buttons (≥ 48 CSS px, preferably 64+) and
  generous spacing.
- **Suppress accidental UI:** `overscroll-behavior: none`, `user-select: none`,
  `-webkit-tap-highlight-color: transparent`, and a context-menu handler on the
  game surface. Avoid disabling pinch-zoom globally for accessibility; disable
  it only on the game surface with `touch-action: none`.
- **Safe areas:** use `viewport-fit=cover` and `env(safe-area-inset-*)` so
  controls are not under a notch or gesture bar.

A virtual joystick is a fixed base with a knob: on `pointerdown`, record the
base center and capture the pointer; on `pointermove`, map the offset to a
normalized vector with a dead zone (0.10–0.15), clamp to the unit circle, and
optionally rescale so full deflection is reachable; on `pointerup`/`pointercancel`,
reset to zero. Buttons are independent pointer targets with their own
`pointerId`s. This gives the phone a private control surface: the TV shows the
game, the phone shows only that player’s buttons, joystick, “ball ready” state,
latency indicator and battery/wake-lock status.

Haptics are a nice-to-have, not a control channel. Chrome for Android supports
`navigator.vibrate()`; it requires sticky user activation and a visible document,
and implementations may cap the pattern (the spec caps entries at 10 s)
`[S26]`. Firefox for Android disables vibration entirely `[S36]`. Use short
10–20 ms taps on button-down; never rely on vibration for gameplay state.

Touch sampling can be higher than 60 Hz on 120 Hz phones, but the sensor pump and
the game loop are 60 Hz `[S6]`; there is no benefit to sending touch updates
faster than the simulation consumes them. Coalesce and send the latest state.

---

## 5. Transport: WebSocket vs WebRTC

### 5.1 WebSocket

The WebSocket API gives a bidirectional message channel over a single TCP
connection `[S17][S18]`. Relevant facts:

- It runs over TCP, with an HTTP Upgrade handshake; `wss` is WebSocket over TLS
  `[S18]`.
- The browser sends an `Origin` header on the handshake, specifically so the
  server can reject cross-origin use `[S18]`. **Validate it server-side.**
- Subprotocols are negotiated with `Sec-WebSocket-Protocol`; use this for
  protocol versioning (`wiiasports.v1`) `[S18]`.
- Binary messages are exposed as `ArrayBuffer` when `binaryType = "arraybuffer"`
  `[S17]`. Use binary for motion; JSON only for handshake/state.
- `bufferedAmount` exposes queued application bytes, and the spec’s own example
  uses it to avoid sending faster than the network can drain `[S17]`. The API has
  **no backpressure**; if messages arrive faster than the app processes them,
  memory/CPU grows `[S19]`. Guard with `bufferedAmount` and drop stale motion.
- Ping/Pong frames exist in the protocol but are **not exposed in the API**
  `[S17]`. Implement an application-level ping/pong if you need liveness/latency.
- Abnormal closures should be recovered with a random initial delay and
  exponential backoff; RFC 6455 recommends exactly that `[S18]`.
- RFC 6455 puts no limit on established connections to one host, though servers
  may refuse excessive connections `[S18]`. A personal console can cap at 4–8.

WebSocket is the right default for this project: one port, one TLS certificate,
simple Python server, trivial bandwidth, and reliable ordered delivery of button
state. Its weakness is TCP head-of-line blocking: a lost packet stalls all later
messages until retransmission. On a clean LAN that is rare; on a congested 2.4
GHz network it can produce 100 ms+ stalls.

### 5.2 WebRTC data channels

WebRTC data channels run SCTP over DTLS over UDP `[S20][S21]`. They are
configurable:

- `ordered: false` allows out-of-order delivery `[S20]`.
- `maxRetransmits: 0` (or a small number) gives unreliable or partially reliable
  delivery `[S20]`.
- This avoids TCP head-of-line blocking for motion; a reliable/ordered channel
  can still be used for discrete commands `[S21]`.

The cost is complexity: signalling, ICE, DTLS, SDP, and ICE candidate handling
`[S22]`. For a browser-to-console LAN connection, host candidates usually connect
directly, but the browser’s IP-handling mode may restrict or obfuscate host
candidates, and the signalling path still needs to be implemented `[S22]`. Chrome has announced plans to apply LNA to WebRTC, but
as of the Chrome 147 release notes only WebSocket and WebTransport were listed
`[S14][S15]`.

**Recommendation:** start with WSS. If measured p95 input age exceeds the budget,
or if packet loss causes visible stalls, add a **second** unreliable/unordered
data channel for motion and keep WSS for buttons/commands. Do not begin with a
full WebRTC stack for a 2 KB/s stream.

### 5.3 Multiple phones

One WebSocket per phone, one player slot per connection. The server keeps a
`PlayerInput` record per slot and reads the latest snapshot in the game loop.
Four phones at 60 Hz × 32 bytes is ~8 KB/s total; Wi-Fi airtime is not the
bottleneck. The real issues are slot assignment, duplicate connections, and
cleanup after a phone sleeps.

Use a room code plus a per-player resume token stored in `localStorage`. On
disconnect, keep the slot for a short grace period (e.g., 15 s), zero its inputs,
and let the same phone resume. If a second connection claims an occupied slot
with a different token, close the old one with a distinct application close code.

---

## 6. PWA: installability, wake lock, fullscreen, orientation, vibration

### 6.1 Installability

Chrome’s install criteria are `[S27]`:

- served over HTTPS
- a web app manifest with `name` or `short_name`, 192 px and 512 px icons,
  `start_url`, and `display` one of `fullscreen`, `standalone`, `minimal-ui`,
  or `window-controls-overlay`
- `prefer_related_applications` absent or `false`
- plus engagement heuristics for the automatic `beforeinstallprompt` promotion
  (the user has interacted and spent some time on the page)

A **service worker is not required** by the current criteria `[S27]`. That is
useful here: a controller is a live LAN app, not an offline app, and a service
worker adds cache-invalidation risk for no gameplay benefit. If you add one for
an offline shell, keep it network-first for the controller page and version it.

Users can install even when the automatic criteria are not met, via the browser
menu `[S27]`. Treat installation as optional: the same page works in a tab with
`requestFullscreen()`.

Manifest settings for this project:

```json
{
  "name": "wiIAsports Controller",
  "short_name": "wiIAsports",
  "start_url": "/play",
  "display": "fullscreen",
  "orientation": "landscape",
  "icons": [
    { "src": "/icons/192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

`display: fullscreen` and `orientation` are manifest members; `orientation` is
the default orientation for the app’s top-level traversables `[S29]`.

### 6.2 Fullscreen

`Element.requestFullscreen()` requires transient user activation and is subject
to the `fullscreen` Permissions Policy `[S28]`. Call it from the “Start” tap,
catch rejection, and keep a usable non-fullscreen layout. Fullscreen is what
hides the browser chrome and makes the phone feel like a controller; it is also
the usual precondition for orientation lock.

### 6.3 Orientation lock

`screen.orientation.lock()` is defined by the Screen Orientation spec. A user
agent **MUST** restrict lock to simple fullscreen documents as a pre-lock
condition, and exiting fullscreen unlocks the orientation `[S24]`. So the order
is: `requestFullscreen()` → `screen.orientation.lock("landscape")` (or
`"portrait"` for bowling). Chrome for Android supports the API (MDN records
Chrome Android 38+); Firefox for Android only from 144 `[S37]`. Always catch and
tolerate failure: some OEMs and some form factors ignore the request.

### 6.4 Wake lock

The Screen Wake Lock API is secure-context only. `navigator.wakeLock.request("screen")`
resolves with a sentinel, may be rejected by system settings (power saving, low
battery) or because the document is not visible, and the lock is automatically
released when the document becomes inactive `[S25]`. Reacquire it on
`visibilitychange` when the page becomes visible again `[S25]`. Show a small
indicator so the player knows the screen will stay on.

A wake lock keeps the **screen** on; it does not keep the browser running in the
background, and it does not override the phone’s battery saver. If the phone
locks or the user switches apps, sensor events stop (the DeviceOrientation spec
returns early when the document is not visible) `[S1]`.

### 6.5 Vibration

`navigator.vibrate()` requires sticky activation and a visible document; patterns
are capped (max 10 entries, max 10 s per entry in the spec) `[S26]`. Chrome for
Android supports it; Firefox for Android disables it `[S36]`. Use it for
confirmation, not for state.

### 6.6 Limitations to design around

- **No background sensors.** Hidden documents do not get orientation events
  `[S1]`; the Generic Sensor API only exposes readings to visible documents
  `[S41]`. A phone that locks or switches apps stops being a controller.
- **60 Hz sensor ceiling.** Chrome’s pump is fixed at 60 Hz `[S6]`; Generic
  Sensor is capped at 60 Hz `[S9]`. This is enough for 60 FPS, but it rules out
  high-rate swing analysis.
- **No raw network access.** The WebSocket API “does not allow for raw access to
  the underlying network” `[S17]`; there is no UDP or custom protocol from a
  normal page. WebRTC data channels provide the unreliable option used here
  `[S20]`.
- **No general network discovery.** The browser does not give you mDNS/SSDP
  scanning; QR pairing is the reliable discovery mechanism. Do not build a
  network scanner.
- **No guaranteed scheduling.** Timers and event delivery can be throttled under
  load or battery saver. Design for “latest state” and tolerate jitter.
- **Interruptions.** Calls, notifications and system dialogs can steal focus and
  release fullscreen/wake lock. Handle `visibilitychange` and `fullscreenchange`.
- **Battery/heat.** Continuous 60 Hz sensors, screen on, Wi-Fi and fullscreen
  drain battery; a 30-minute game is fine, an all-day session is not.

---

## 7. Pairing and discovery

### 7.1 QR code is the discovery mechanism

The console displays a QR code containing the controller URL:

```
https://192.168.1.50:8443/play?room=ABCD&token=<128-bit-token>
```

The phone’s camera app opens it; no app install and no typing. If the console has
multiple interfaces, show the QR for the address on the default-route LAN
interface, and offer “show another address” for VPN/Docker/extra NIC cases.
Filter out loopback, link-local, Docker bridges and VPN interfaces.

Use an IP literal in the QR by default (and include the IP in the certificate’s
SAN if you do). A `.local` hostname is mDNS, specified by RFC 6762 `[S40]`, but
Android’s resolver behavior varies; treat `.local` as an optional convenience,
not the only path. A DHCP reservation for the console avoids regenerating the QR
when the lease changes.

### 7.2 Minimal auth

For a personal LAN console, a full account system is overkill. Use:

- a **128-bit random room token** generated per session, embedded in the QR URL
- a **per-player resume token** stored in `localStorage` after the first join
- an **`Origin` check** on the WebSocket handshake, comparing against the exact
  expected origin `[S18]`
- a connection cap (e.g., 4 players + 1 spectator), a message size cap and a
  simple rate limit
- TLS (`wss://`, TLS 1.2+) so the token is not observable on the LAN
- `Referrer-Policy: no-referrer` on the controller page, and no external
  resources, so the token in the URL does not leak via `Referer`
- a strict CSP (`default-src 'self'; connect-src 'self'`) and no inline script
- rotate the room token when the game session ends

This stops casual LAN passers-by and cross-site WebSocket abuse, but it is not a
defense against someone who can see the TV/QR code. For a party game that is the
right threat model. If you need more, add a short PIN displayed on the TV and
typed on the phone, or per-player tokens delivered out of band.

**Never expose the console’s WSS port to the public internet.** Bind it to the
LAN interface, firewall it, and do not port-forward it.

### 7.3 Multiple phones

One room, up to N slots. The first phone to join gets the lowest free slot; the
console shows “Player 2 connected”. A phone that reconnects with its resume token
gets its old slot back within the grace period. When the room is full, allow a
spectator connection that receives state but sends no input. The console should
have a “kick” control per slot.

---

## 8. Recommended stack

### Phone

- **Chrome for Android** as the reference browser.
- A **small PWA**: plain HTML/CSS/JS is enough; no framework is required for a
  controller. If you use a framework, keep it out of the input hot path.
- **Pointer Events** for buttons/joystick; `touch-action: none` on the game
  surface; `setPointerCapture` per finger `[S23]`.
- **`devicemotion`** for bowling swing and optional spin; **`deviceorientation`**
  for kart tilt. Feature-detect and call `requestPermission()` defensively on
  the first tap `[S1][S10]`.
- **WebSocket over WSS** with binary frames; `binaryType = "arraybuffer"`;
  application-level ping/pong; exponential-backoff reconnect `[S17][S18]`.
- **Screen Wake Lock**, **Fullscreen**, **Screen Orientation lock**, optional
  **Vibration** `[S24][S25][S26][S28]`.
- A `manifest.webmanifest` with `display: fullscreen`, `orientation:
  landscape`, 192/512 icons `[S27][S29]`.
- A service worker is optional; skip it unless you want an offline shell.

### Console

- **Python asyncio**; `aiohttp` (HTTP static files + WebSocket on one port) or
  `websockets` plus a small static-file handler, with `ssl.SSLContext` for TLS.
- Serve the PWA and the WSS endpoint from the **same origin and port** (e.g.,
  `https://console.local:8443` and `wss://console.local:8443/ws`). This keeps
  the WebSocket same-origin and avoids the LNA public→local prompt `[S16]`.
- Generate the QR code server-side (e.g., `segno`) with the LAN URL and token.
- An **input hub** with one `PlayerInput` per slot, read by the game loop at 60
  Hz. The Wii Remote is another input source in the same hub; the browser does
  not need to know about it.
- A **session/room manager** for tokens, slots, resume, timeouts and kick.
- An **instrumentation** endpoint/log for RTT, jitter and input age.

### TLS

- **Primary for personal use:** local CA (mkcert-style), leaf cert with SANs for
  `console.local` and the LAN IP, CA installed once on the phone. Chrome’s
  Android verifier loads user-added roots `[S33]`.
- **Primary for zero phone-side setup:** public domain + Let’s Encrypt DNS-01,
  A record to the LAN IP `[S34]`.
- **Fallback:** tunnel, only if you accept off-LAN traffic and its latency.
- **Dev only:** `adb reverse` + `http://localhost:8443` `[S4]`.

### Transport

- **WSS first.** Measure p50/p95 input age for a real session.
- **WebRTC unreliable/unordered** only if the measurement says WSS is the
  problem (Wi-Fi loss / head-of-line stalls), not because it sounds lower
  latency `[S20][S21]`.
- If you add WebRTC, keep buttons/commands on the reliable WSS path and put only
  motion on the unreliable data channel.

---

## 9. Minimal protocol sketch

### 9.1 Handshake

WebSocket URL:

```
wss://console.local:8443/ws?room=ABCD&token=<token>&slot=auto
Sec-WebSocket-Protocol: wiiasports.v1
```

Client → server (text JSON, once):

```json
{
  "t": "hello",
  "v": 1,
  "room": "ABCD",
  "token": "<token>",
  "resume": "<optional-player-token>",
  "caps": { "motion": true, "orientation": true, "vibrate": true }
}
```

Server → client (text JSON, once):

```json
{
  "t": "welcome",
  "player": 2,
  "rate": 60,
  "resume": "<player-token>",
  "config": { "deadzone": 0.12, "motion": true, "orientation": false }
}
```

After `welcome`, both directions use binary frames. The server must validate the
`Origin` header and the token before sending `welcome`; on failure close with an
application code (e.g., 4001) and a short reason `[S18]`.

### 9.2 Binary framing

All integers little-endian. Header is 8 bytes:

| Offset | Type | Field |
|---:|---|---|
| 0 | `u8` | type |
| 1 | `u8` | flags (reserved, 0) |
| 2 | `u16` | sequence number |
| 4 | `u32` | client monotonic time, ms (wraps ~49 days) |

Packet types:

| Type | Name | Payload | Total |
|---:|---|---|---:|
| `0x01` | Motion | `f32 ax, ay, az` (m/s² including gravity) + `f32 gx, gy, gz` (deg/s) | 32 B |
| `0x02` | Buttons | `u16 mask` + `i16 leftX` + `i16 leftY` | 14 B |
| `0x03` | Orientation | `f32 alpha, beta, gamma` (deg) | 20 B |
| `0x04` | Ping | `u32 t_ms` | 12 B |
| `0x05` | Pong | `u32 echo` + `u32 server_ms` | 16 B |
| `0x06` | Haptic | `u8 pattern` + `u16 duration_ms` + `u8 intensity` | 12 B |
| `0x07` | Config | UTF-8 JSON (rare) | variable |

Types `0x01`–`0x04` are client→server; `0x05`–`0x07` are server→client. Define
the button mask per game; for example, bit 0 = release, bit 1 = spin, bit 2 =
gas, bit 3 = brake.

Sizes include the 8-byte header. At 60 Hz, one phone sends:

- motion: 32 × 60 = **1,920 B/s**
- orientation (if enabled): 20 × 60 = **1,200 B/s**
- buttons on change + 5 Hz keepalive: ~**70 B/s**
- ping 1 Hz: **12 B/s**

So ~2–3.3 KB/s per phone, <15 KB/s for four phones. This is negligible for
Wi-Fi; the latency budget is dominated by sampling and the game loop, not
bandwidth.

### 9.3 Send policy

- **Motion/orientation:** send the latest sample at 60 Hz. Do not queue. If
  `ws.bufferedAmount > 2048`, skip this sample and send the next one; stale
  motion is worse than a gap. This is the WebSocket equivalent of dropping old
  frames, since the API has no backpressure `[S17][S19]`.
- **Buttons:** send a state snapshot on every change and repeat at 5 Hz. The
  server applies the latest mask; a lost/reordered snapshot is self-correcting.
- **Ping:** every 1 s; if no pong for 3 s, close and reconnect. The browser’s
  WebSocket API does not expose protocol ping/pong, so this must be application
  level `[S17]`.
- **Sequence:** `u16`, wrap-aware comparison. The server ignores older motion
  samples and always keeps the newest button mask.
- **Reconnect:** random initial delay, then exponential backoff with jitter,
  capped at ~10 s, reset on a successful `welcome` `[S18]`.
- **Resume:** on reconnect, send the stored player token; the server restores
  the slot if within the grace period, otherwise assigns a new one.

### 9.4 Server-side sketch

```python
# Pseudocode; adapt to your server library.
@dataclass
class PlayerInput:
    seq: int = 0
    t_ms: int = 0
    ax: float = 0.0; ay: float = 0.0; az: float = 0.0
    gx: float = 0.0; gy: float = 0.0; gz: float = 0.0
    alpha: float = 0.0; beta: float = 0.0; gamma: float = 0.0
    buttons: int = 0
    left_x: float = 0.0; left_y: float = 0.0
    last_seen: float = 0.0

# On binary message:
#   type, flags, seq, t_ms = struct.unpack_from("<BBHI", data, 0)
#   if newer(seq, player.seq):
#       decode payload with struct.unpack_from("<ffffff", data, 8)
#       update player fields; player.last_seen = monotonic()
# Game loop at 60 Hz:
#   for p in players:
#       if monotonic() - p.last_seen > 0.2: p.buttons = 0; p.left_x = p.left_y = 0
#       apply(p)
```

Decode in the network task, not in the render loop. Keep the last snapshot per
player; never build an unbounded queue. If a player is stale for ~200 ms (12
frames), zero their inputs; if stale for ~2 s, mark disconnected but keep the
slot during the grace period.

### 9.5 Client-side start sequence

1. User taps “Start controller”.
2. `requestFullscreen()` (catch failure).
3. `screen.orientation.lock("landscape")` (catch failure).
4. `navigator.wakeLock.request("screen")` (catch failure; show indicator).
5. `DeviceMotionEvent.requestPermission()` / `DeviceOrientationEvent.requestPermission()`
   if present; else listen directly.
6. Open WSS; send `hello`; wait for `welcome`.
7. Start sending at 60 Hz; start ping timer.
8. On `visibilitychange` hidden: stop sending, release wake lock; on visible:
   reacquire, recalibrate neutral, resume.
9. On `close`: show reconnect overlay, backoff, retry; keep the last local state
   so the player does not lose their slot.

---

## 10. Latency and rate expectations

### 10.1 What is actually achievable

There is **no primary-source number for “typical LAN latency”**. It depends on
Wi-Fi generation, channel congestion, power saving, distance, and the phone’s
network stack. Treat any number as an engineering expectation to be measured,
not a guarantee. On a clean 5 GHz network, single-digit-millisecond RTT is
common; on a congested 2.4 GHz network, tens of milliseconds and occasional
100 ms+ spikes are possible. Measure it in the actual room.

The parts that **are** defined:

| Stage | Budget | Source |
|---|---:|---|
| Sensor sample to browser event | 0–16.7 ms (60 Hz pump; mean 8.3) | `[S6][S8]` |
| Event handler to `ws.send()` | < 1 ms | engineering estimate |
| LAN one-way | 0.5–5 ms typical; measure | empirical, not standardized |
| Server parse + input update | < 1 ms | engineering estimate |
| Game loop sampling | 0–16.7 ms (60 Hz; mean 8.3) | 60 FPS arithmetic |
| **Input-to-game-state** | **~20–35 ms typical, ~45 ms worst + jitter** | derived |

So the **under-50 ms input-to-game-state target is realistic** on a healthy LAN,
but it is not free: the 60 Hz sensor pump and the 60 Hz game loop each contribute
up to a frame. If the game loop runs at 120 Hz internally and reads the latest
input every tick, the loop term halves; that is a cheap improvement if the
simulation can tolerate it.

**Input-to-photon is a different budget.** Add the TV’s display latency, which
can be 10–30 ms in game mode and much worse in “cinema”/processing modes. The
browser cannot control it. Measure the TV; use game mode. If the target is
input-to-photon < 50 ms, the TV may be the limiting factor even when the network
and game loop are fine.

### 10.2 Measurement

Add an application-level ping every 1 s:

```js
const t0 = performance.now();
ws.send(encodePing(t0));
// on pong: rtt = performance.now() - echo
```

Log p50/p95 and max RTT; show a small latency/jitter indicator on the phone.
Also record the age of each motion sample at send time:

```js
const age = performance.now() - event.timeStamp; // ms since event creation
```

`event.timeStamp` is a DOMHighResTimeStamp on the same time origin as
`performance.now()` `[S42]`, so this is a useful “sensor-to-send” estimate (it
does not include the hardware’s own sampling delay, and its precision may be
reduced by the browser `[S42]`). Send the sequence number and client timestamp in
the packet so the server can log gaps and reordering.

### 10.3 When to change the transport

Use WSS unless **measured** p95 input age exceeds ~50 ms or Wi-Fi loss produces
visible stalls. Then:

1. Improve Wi-Fi first: 5 GHz, clean channel, close to the AP, disable aggressive
   power saving if possible.
2. If TCP head-of-line blocking is the cause, add an unreliable/unordered WebRTC
   data channel for motion `[S20][S21]`.
3. If the browser’s 60 Hz ceiling is the cause, go native (Section 12).

Do not switch to WebRTC just because it is “lower latency” in theory; the setup,
ICE and DTLS complexity is real `[S22]`.

---

## 11. Game mappings

### 11.1 Bowling

**Inputs:** swing (acceleration + rotation), release button, optional aim/tilt,
optional spin.

- Hold the phone in the bowling hand, screen facing the player or sideways.
  Calibrate a neutral pose at “ready”: record the gravity vector from
  `accelerationIncludingGravity` and the initial orientation.
- Use `devicemotion` at 60 Hz `[S6][S8]`. Low-pass the accelerometer to estimate
  gravity, subtract it to get linear acceleration, and integrate/combine with
  `rotationRate` to detect the backswing and forward swing. A simple threshold
  on forward acceleration plus a gyro peak is enough for a first version; a
  proper swing detector can come later.
- Detect release from the button (`pointerdown`/`pointerup`) and/or a sharp
  deceleration. Send a `buttons` snapshot immediately; do not wait for the next
  motion frame.
- Optional aim: before the swing, use `deviceorientation` `gamma` (left/right
  tilt) or the gravity vector’s projection. Show the aim on the phone, not the
  TV, if it is private information.
- Optional spin: at release, use `rotationRate` around the appropriate axis
  (deg/s) or `deviceorientation` `alpha` change. Calibrate the axis for the
  player’s grip; do not assume a fixed axis across phones.
- Haptics: a short tap on release if `navigator.vibrate` is available and the
  document is visible `[S26]`.

**Why `devicemotion`:** it fires unconditionally at 60 Hz, while
`deviceorientation` only fires on >0.1° change `[S7]`; a swing is exactly the
kind of fast transient you do not want to miss. Use `deviceorientation` only for
the slow aim/calibration part.

### 11.2 Kart

**Inputs:** tilt/steer, gas/brake buttons, optional drift.

- Lock landscape (`manifest.orientation` + `screen.orientation.lock`) `[S24][S29]`.
- Use `deviceorientation` `gamma` (roll) for steering, with `beta` as a sanity
  check. Calibrate neutral at “ready” (phone held comfortably), subtract it, apply
  a dead zone (~0.1–0.15), normalize to [-1, 1], and low-pass the result.
- Because `deviceorientation` only fires when the angle changes `[S7]`, the last
  value is the correct steering value while the phone is still. This is a
  feature, not a bug: no jitter when holding a line.
- If `deviceorientation` is unavailable, fall back to `devicemotion`’s gravity
  vector and compute the tilt from the accelerometer.
- Gas/brake are buttons; use `pointerdown`/`pointerup` with pointer capture
  `[S23]`. Consider a large “gas” area and a smaller “brake” area; both must be
  reachable with the thumbs while tilting.
- Optional drift: a button plus steering angle; do not require gyro integration
  for the first version.

### 11.3 Alongside the Wii Remote

The phone is just another input source. On the console, define a common input
snapshot (buttons, axes, motion) and merge sources by player slot. The Wii
Remote path is Linux-side (kernel driver/evdev or an existing library); the
browser path is WSS. The game should not care which device produced the input.
The only shared concern is latency: timestamp both sources at ingest and use the
same “latest state” policy.

---

## 12. Native alternatives — only if the browser cannot deliver

The browser can deliver 60 Hz motion, multitouch, WSS, PWA/fullscreen, wake lock,
orientation lock and vibration. A native Android app is justified only for one
of these:

| Need | Browser | Native |
|---|---|---|
| > 60 Hz sensor sampling | Capped at 60 Hz in Chrome `[S6][S9]` | `SensorManager` at `SENSOR_DELAY_GAME` (20 ms) or `SENSOR_DELAY_FASTEST` `[S30]`; Android 12+ caps at 200 Hz unless `HIGH_SAMPLING_RATE_SENSORS` `[S30]` |
| Sensors while screen off / app backgrounded | Stops when document is hidden `[S1]` | Foreground service; Android 9+ restricts background sensors, so a foreground service is required `[S30]` |
| Sub-10 ms / UDP / no TCP head-of-line | No raw sockets `[S17]`; WebRTC only | Direct `DatagramSocket` UDP |
| Avoiding TLS/CA setup | HTTPS required for sensors `[S1][S4]` | Cleartext LAN is possible if the app opts in; Android 9+ disables cleartext by default `[S32]` |
| Rich haptics / special hardware | Vibration API only `[S26]` | `VibratorManager`, sensor fusion, etc. |

A minimal native stack: Kotlin, `SensorManager` with `SENSOR_DELAY_GAME` (50 Hz,
20 ms) or `SENSOR_DELAY_FASTEST` `[S30]`, a foreground service, OkHttp WebSocket
(or UDP), `FLAG_KEEP_SCREEN_ON`, immersive mode, `setRequestedOrientation`, and
`VibratorManager`. Use `SensorEvent.timestamp` (ns) for precise timing. If you
need user-installed CAs in the native app, note that apps targeting Android 6.0
(API 23) and lower trust user CAs by default, while newer apps need a network
security config `[S32]` — or just use cleartext on the LAN with an explicit
opt-in.

**Cost:** a native app is roughly a day or two of extra work plus sideloading and
update friction, versus hours for the PWA. Do it only after measuring that the
browser is the bottleneck.

---

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No trusted HTTPS on LAN; sensors/PWA blocked | High | High | Local CA installed once, or public domain + LE DNS-01; test on the actual phone |
| Chrome’s sensor permission moves to Ask | Medium | Medium | Call `requestPermission()` on first tap now; handle denial; feature-detect `[S10][S11]` |
| `requestPermission()` behavior differs on OEM/Chrome version | Medium | Medium | Test on the target phone; always keep a touch-only fallback |
| 60 Hz sensor cap too coarse for swing | Low–Medium | Medium | Use `devicemotion` + filtering; if still insufficient, native `SENSOR_DELAY_GAME`/`FASTEST` |
| `deviceorientation` too sparse when still | Low | Low | Hold last value for steering; use `devicemotion` for dynamics `[S7]` |
| Coordinate-frame mistake in landscape | Medium | High | Remap with `screen.orientation.angle`, lock orientation, calibrate neutral `[S1][S31]` |
| Wi-Fi jitter / head-of-line stalls | Medium | High | 5 GHz, clean channel, measure p95; WebRTC unreliable fallback `[S20][S21]` |
| Phone locks / app switches; sensors stop | High | High | Wake lock, fullscreen, visibility handling; design a pause/resume flow `[S25]` |
| TLS cert expires / clock skew | Medium | High | Automate renewal; monitor expiry; allow a local CA with a long leaf life |
| Token leaked via QR/screenshot/referrer | Low–Medium | Medium | Short TTL, rotate per session, `no-referrer`, no external resources, Origin check `[S18]` |
| Cross-site WebSocket abuse | Medium | Medium | Validate `Origin`, token, connection cap, rate limit `[S18]` |
| LNA expansion breaks public-page-to-LAN design | Medium | High | Serve the page from the LAN origin; avoid public tunnels `[S14][S16]` |
| Firefox Android differences (vibration, orientation lock, certificate trust) | Medium | Low | Chrome is the reference; test Firefox separately or declare it unsupported `[S36][S37][S38]` |
| PWA install/WebAPK behavior varies | Low | Low | Treat install as optional; fullscreen in a tab works `[S27][S28]` |
| Multiple phones conflict on slots | Medium | Low | Resume tokens, slot lease, kick control, server-side cap |

---

## 14. Open questions

These are the things this desk research cannot settle; they need a test on the
actual phone, console and Wi-Fi.

1. **Chrome 151+ permission behavior on the target phone.** Does
   `requestPermission()` return `granted` immediately under the default Allow, or
   does it prompt? Does the page still receive events if it never calls it? Test
   on the target OEM/Android version. The source says default Allow and future
   Ask `[S11][S12]`, but the transition is in flight.
2. **Does Chrome on the target phone trust the mkcert CA?** The Chromium source
   loads user-added roots `[S33]`, but Android OEMs differ in the CA-install UI
   and in whether the CA is visible. Test the exact phone/Android build.
3. **p50/p95 input age on the target Wi-Fi and TV.** Measure with the app-level
   ping and `event.timeStamp`; test 2.4 GHz vs 5 GHz, near vs far from the AP.
4. **Is `deviceorientation` dense enough for kart steering at 60 Hz?** It fires
   only on >0.1° change `[S7]`; for small steering corrections it may be sparse.
   Compare it with a `devicemotion` gravity-vector steering implementation.
5. **Which signal is best for bowling swing?** Compare
   `accelerationIncludingGravity`, linear acceleration, `rotationRate`, and a
   fused orientation on real throws. Decide whether to compute the swing on the
   phone or send raw samples to the console.
6. **Does the phone’s PWA fullscreen + orientation lock actually hold on the
   target OEM?** Test `display: fullscreen`, `requestFullscreen()`,
   `screen.orientation.lock()`, and wake lock together, including a call
   interruption.
7. **Is WebRTC needed at all?** Only if measured Wi-Fi loss causes visible TCP
   stalls. If yes, test `ordered: false, maxRetransmits: 0` on a second data
   channel `[S20]`.
8. **Does installing the PWA require internet for WebAPK minting on the target
   phone?** If yes, the home-screen shortcut may be the only offline install
   path. Treat install as optional.
9. **Does Firefox for Android matter for this project?** If yes, verify sensor
   delivery, certificate trust, vibration (disabled `[S36]`) and orientation lock
   (144+ `[S37]`).
10. **Can the TV be put in game mode?** Input-to-photon may be dominated by the
    display; measure before optimizing the network further.

---

## Sources

Each source is cited inline as `[S#]`. Primary sources are specs, browser
documentation and browser source code; a few sources are first-party
compatibility data or vendor documentation.

| ID | Source | What it supports |
|---|---|---|
| S1 | [W3C Device Orientation and Motion (Editor’s Draft)](https://w3c.github.io/deviceorientation/) | Secure-context requirement, permissions policy, `requestPermission()`, coordinate system, alpha/beta/gamma, acceleration/rotation-rate units, visibility check, 1° threshold recommendation |
| S2 | [MDN `DeviceMotionEvent`](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent) | API surface, secure context, Chrome/Firefox Android support |
| S3 | [MDN `DeviceOrientationEvent`](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent) | API surface, Chrome relative-orientation note, Chrome/Firefox Android support |
| S4 | [MDN Secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts) | HTTPS/localhost are secure; private IP HTTP is not |
| S5 | [MDN Mixed content](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Mixed_content) | Insecure requests from HTTPS pages are blockable; localhost is secure |
| S6 | [Chromium `device_sensor_event_pump.h`](https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/modules/device_orientation/device_sensor_event_pump.h) | Fixed 60 Hz sensor pump (`kDefaultPumpFrequencyHz = 60`) |
| S7 | [Chromium `device_orientation_event_pump.cc`](https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/modules/device_orientation/device_orientation_event_pump.cc) | `deviceorientation` dispatch threshold `kOrientationThreshold = 0.1`° |
| S8 | [Chromium `device_motion_event_pump.cc`](https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/modules/device_orientation/device_motion_event_pump.cc) | `devicemotion` sources (accelerometer, linear acceleration, gyro), fixed 16 ms interval, NaN fallback |
| S9 | [Chromium `sensor_traits.h`](https://chromium.googlesource.com/chromium/src/+/main/services/device/public/cpp/generic_sensor/sensor_traits.h) | Generic Sensor max 60 Hz, default 10 Hz for motion sensors |
| S10 | [Chrome 151 release notes](https://developer.chrome.com/release-notes/151) | `DeviceOrientationEvent.requestPermission()` / `DeviceMotionEvent.requestPermission()` shipped |
| S11 | [ChromeStatus: DeviceOrientation Events permission request API](https://chromestatus.com/feature/5915984063889408) | Default-Allow phase; plan to move to Ask; WebView always grants |
| S12 | [Chromium issue 40094424, comment 87](https://issues.chromium.org/issues/40094424#comment87) | Tri-state allow/ask/block model being added; default remains Allow (March 2026) |
| S13 | [Chrome 142 release notes](https://developer.chrome.com/release-notes/142) | LNA restrictions: public→local/loopback, permission prompt, secure context |
| S14 | [Chrome 147 release notes](https://developer.chrome.com/release-notes/147) | LNA applies to WebSockets and WebTransport; definition of local network request; permission-gated |
| S15 | [Chrome blog: New permission prompt for Local Network Access](https://developer.chrome.com/blog/local-network-access) | LNA scope, secure context, mixed-content exemption for local `fetch()`, WebSocket/WebRTC plans |
| S16 | [WICG Local Network Access spec](https://wicg.github.io/local-network-access/) | Local network request definition, same-origin exemption, Chromium-only public→local enforcement, WebSocket integration, no `targetAddressSpace` for `ws://` |
| S17 | [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/) | WebSocket API, `binaryType`, `bufferedAmount`, no ping/pong API, no raw network access, close semantics |
| S18 | [RFC 6455 — The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455) | TCP transport, Origin header, subprotocol negotiation, reconnect backoff, no established-connection limit |
| S19 | [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) | No backpressure; WebTransport alternative; bfcache note |
| S20 | [MDN `RTCDataChannel`](https://developer.mozilla.org/en-US/docs/Web/API/RTCDataChannel) | SCTP/DTLS, `ordered`, `maxRetransmits`, `bufferedAmount`, `open`/`close` |
| S21 | [MDN Using WebRTC data channels](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Using_data_channels) | DTLS encryption, head-of-line blocking, message size |
| S22 | [RFC 8828 — WebRTC IP Address Handling](https://www.rfc-editor.org/rfc/rfc8828) | ICE, host candidates, private-IP privacy considerations |
| S23 | [MDN Pointer events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events) | `pointerId`, `isPrimary`, `setPointerCapture`, `pointercancel`, `touch-action` |
| S24 | [W3C Screen Orientation spec](https://w3c.github.io/screen-orientation/) | `lock()` pre-lock condition requiring fullscreen; unlock on exit |
| S25 | [MDN Screen Wake Lock API](https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API) | Secure context, visible document, request/release, reacquire on `visibilitychange` |
| S26 | [W3C Vibration API](https://w3c.github.io/vibration/) | Sticky activation, visible document, max pattern/duration |
| S27 | [web.dev: PWA install criteria](https://web.dev/articles/install-criteria) | HTTPS, manifest fields, 192/512 icons, display values, engagement heuristics, no service-worker requirement |
| S28 | [MDN `Element.requestFullscreen()`](https://developer.mozilla.org/en-US/docs/Web/API/Element/requestFullscreen) | Transient activation requirement, Permissions Policy, promise rejection |
| S29 | [W3C Web Application Manifest](https://www.w3.org/TR/appmanifest/) | `display`, `orientation`, `start_url`, `icons`, manifest application |
| S30 | [Android Sensors Overview](https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview) | `SENSOR_DELAY_GAME` 20 ms, `SENSOR_DELAY_FASTEST` 0, 200 Hz cap API 31+, `HIGH_SAMPLING_RATE_SENSORS`, foreground-only sensors |
| S31 | [Android Motion Sensors](https://developer.android.com/develop/sensors-and-location/sensors/sensors_motion) | Accelerometer/gyroscope/linear acceleration/rotation vector, natural-orientation coordinate system, sensor availability |
| S32 | [Android Network Security Configuration](https://developer.android.com/privacy-and-security/security-config) | Apps targeting API 24+ do not trust user CAs by default; cleartext disabled by default on Android 9+ |
| S33 | [Chromium `trust_store_android.cc`](https://chromium.googlesource.com/chromium/src/+/main/net/cert/internal/trust_store_android.cc) | Chrome’s Android verifier loads `net::android::GetUserAddedRoots()` |
| S34 | [Let’s Encrypt: Challenge Types](https://letsencrypt.org/docs/challenge-types/) | DNS-01 works without a publicly reachable web server; DNS-01 cannot validate IPs; HTTP-01/TLS-ALPN-01 can |
| S35 | [Let’s Encrypt: We’ve Issued Our First IP Address Certificate](https://letsencrypt.org/2025/07/01/issuing-our-first-ip-address-certificate) | IP certs must be short-lived; no DNS-01 for IPs |
| S36 | [MDN `Navigator.vibrate()`](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/vibrate) | Chrome Android support and user-gesture note; Firefox Android vibration disabled |
| S37 | [MDN `ScreenOrientation.lock()`](https://developer.mozilla.org/en-US/docs/Web/API/ScreenOrientation/lock) | Firefox Android support only from 144; earlier partial/broken |
| S38 | [MDN `DeviceMotionEvent.requestPermission()`](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/requestPermission_static) | Chrome 151+ (Chrome release notes; MDN BCD records 152); Firefox/Firefox Android not supported |
| S39 | [MDN `WakeLock`](https://developer.mozilla.org/en-US/docs/Web/API/WakeLock) | Chrome 84+, Firefox 126+ (including Android) |
| S40 | [RFC 6762 — Multicast DNS](https://www.rfc-editor.org/rfc/rfc6762) | `.local` naming is mDNS; resolution support is not guaranteed by the browser/OS |
| S41 | [W3C Generic Sensor API (Editor’s Draft)](https://w3c.github.io/sensors/) | Sensor readings only exposed to visible documents; secure context/permissions integration |
| S42 | [MDN `Event.timeStamp`](https://developer.mozilla.org/en-US/docs/Web/API/Event/timeStamp) | Timestamp is relative to the time origin; precision may be reduced |
