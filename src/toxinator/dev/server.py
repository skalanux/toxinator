"""HTTP/HTTPS + WebSocket development server for the phone controller."""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from aiohttp import WSMsgType, web

from toxinator.input.phone.registry import PhoneRegistry

logger = logging.getLogger(__name__)

PROTOCOL = 2
MAX_PHOTO_BYTES = 2 * 1024 * 1024
MIN_PHOTO_BYTES = 16 * 1024
MAX_ASSET_BYTES = 4 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg": "jpg", "image/png": "png"}
ASSET_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class DevServer:
    """Serve the PWA and its WebSocket on one origin.

    The default is plain HTTP/WS so the phone can connect without accepting a
    certificate. With TLS, serving both on the same origin lets the certificate
    exception accepted for the page cover ``wss://`` too.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        controller_web: Path,
        ssl_context: ssl.SSLContext | None,
        token: str,
        registry: PhoneRegistry,
    ) -> None:
        self._host = host
        self._port = port
        self._controller_web = controller_web
        self._ssl = ssl_context
        self._token = token
        self._registry = registry
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._error: Exception | None = None
        self._lock = threading.Lock()
        self._clients: dict[web.WebSocketResponse, int] = {}
        self._mode = "launcher"
        self._controller: dict[str, Any] | None = None
        self._panel: dict[str, Any] | None = None
        self._game_id = ""
        self._game_assets: Path | None = None
        self._photos: dict[int, dict[str, Any]] = {}

    def start(self) -> None:
        if self._thread is not None:
            return
        if not self._controller_web.is_dir():
            raise RuntimeError(f"controller-web no existe: {self._controller_web}")
        self._thread = threading.Thread(
            target=self._run,
            name="toxinator-dev-server",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=10.0):
            raise RuntimeError("el servidor de desarrollo no arrancó")
        if self._error is not None:
            raise RuntimeError(
                f"no pude abrir el servidor en {self._host}:{self._port}: {self._error}"
            ) from self._error
        scheme = "https" if self._ssl is not None else "http"
        logger.info("phone controller en %s://%s:%s", scheme, self._host, self._port)

    def set_mode(self, mode: str) -> None:
        with self._lock:
            self._mode = mode
        self._broadcast({"type": "mode", "mode": mode})

    def set_controller(self, profile: dict[str, Any] | None) -> None:
        """Publish the selected game's controller layout and skin."""
        panel = None
        with self._lock:
            self._controller = dict(profile) if profile is not None else None
            controller = self._controller
            if controller is not None and isinstance(controller.get("panel"), dict):
                panel = dict(controller["panel"])
            self._panel = panel
            payload = self._panel_payload_locked()
        self._broadcast({"type": "controller", "profile": controller})
        self._broadcast({"type": "panel", "panel": payload})

    def set_panel(self, panel: Mapping[str, Any] | None) -> None:
        """Show a static panel (title, image, fit) on the phone, or clear it."""
        with self._lock:
            self._panel = dict(panel) if panel is not None else None
            payload = self._panel_payload_locked()
        self._broadcast({"type": "panel", "panel": payload})

    def clear_panel(self) -> None:
        self.set_panel(None)

    def set_game_assets(self, game_id: str, root: Path | None) -> None:
        """Allow the active game's asset directory to be served to the phone."""
        with self._lock:
            self._game_id = game_id
            self._game_assets = root.resolve() if root is not None else None

    def send_haptic(self, pattern: int | Sequence[int], slot: int | None = None) -> None:
        """Send a vibration pattern to one phone or all phones."""
        raw = [pattern] if isinstance(pattern, int) else list(pattern)
        values = [
            max(0, min(5000, int(value))) for value in raw if isinstance(value, (int, float))
        ][:12]
        logger.info("phone haptic slot=%s pattern=%s", slot, values)
        self._broadcast({"type": "haptic", "pattern": values}, slot=slot)

    def send_audio_tone(
        self,
        frequency: float,
        duration_ms: int,
        *,
        volume: float = 0.35,
        slot: int | None = None,
    ) -> None:
        """Play a short sine tone on the phone speaker."""
        payload = {
            "type": "audio",
            "action": "tone",
            "frequency": max(40.0, min(12000.0, float(frequency))),
            "duration": max(20, min(5000, int(duration_ms))),
            "volume": max(0.0, min(1.0, float(volume))),
        }
        logger.info(
            "phone audio slot=%s tone=%sHz/%sms",
            slot,
            payload["frequency"],
            payload["duration"],
        )
        self._broadcast(payload, slot=slot)

    def send_audio_stop(self, slot: int | None = None) -> None:
        self._broadcast({"type": "audio", "action": "stop"}, slot=slot)

    def recenter(self, slot: int | None = None) -> None:
        """Recalibrate the neutral pose and reset aim on one phone or all."""
        slots = [slot] if slot is not None else list(range(self._registry.max_slots))
        for target in slots:
            self._registry.calibrate(target)
        self._broadcast({"type": "calibrated"}, slot=slot)

    def last_photo(self, slot: int) -> tuple[str, bytes] | None:
        """Return the last uploaded photo for a slot, if any."""
        with self._lock:
            photo = self._photos.get(slot)
            if photo is None:
                return None
            return (str(photo["id"]), bytes(photo["data"]))

    def _panel_payload_locked(self) -> dict[str, Any] | None:
        panel = self._panel
        if panel is None:
            return None
        image = panel.get("image")
        payload = {
            "title": str(panel.get("title", ""))[:40],
            "fit": str(panel.get("fit", "contain")),
            "url": None,
        }
        if isinstance(image, str) and image and self._game_assets is not None:
            payload["url"] = f"/game-assets/{self._game_id}/{image.lstrip('/')}"
        elif isinstance(panel.get("url"), str):
            payload["url"] = panel["url"]
        return payload

    def _broadcast(self, payload: dict[str, Any], *, slot: int | None = None) -> None:
        with self._lock:
            clients = [
                client
                for client, client_slot in self._clients.items()
                if slot is None or client_slot == slot
            ]
        loop = self._loop
        if loop is None or not clients:
            return

        async def send() -> None:
            encoded = json.dumps(payload)
            for client in clients:
                try:
                    await client.send_str(encoded)
                except Exception:
                    continue

        asyncio.run_coroutine_threadsafe(send(), loop)

    def stop(self) -> None:
        loop = self._loop
        event = self._stop_event
        if loop is not None and event is not None:
            loop.call_soon_threadsafe(event.set)
        if self._thread is not None:
            self._thread.join(timeout=10.0)
            self._thread = None

    def _run(self) -> None:
        try:
            asyncio.run(self._serve())
        except Exception as error:
            self._error = error
            logger.error("dev server failed: %s", error)
            self._ready.set()

    def make_app(self) -> web.Application:
        """Build the aiohttp application (web routes only, no sockets)."""
        app = web.Application(client_max_size=MAX_PHOTO_BYTES + 64 * 1024)
        app.router.add_get("/", self._index)
        app.router.add_get("/manifest.webmanifest", self._manifest)
        app.router.add_get("/sw.js", self._service_worker)
        app.router.add_get("/ws", self._websocket)
        app.router.add_post("/api/photo", self._photo)
        app.router.add_get("/game-assets/{game_id}/{tail:.*}", self._game_asset)
        app.router.add_static("/static/", self._controller_web)
        return app

    async def _serve(self) -> None:
        app = self.make_app()

        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(
            runner,
            self._host,
            self._port,
            ssl_context=self._ssl,
        )
        await site.start()

        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        self._ready.set()
        try:
            await self._stop_event.wait()
        finally:
            await runner.cleanup()

    async def _index(self, request: web.Request) -> web.StreamResponse:
        return self._html_response("index.html", cache="no-cache")

    async def _manifest(self, request: web.Request) -> web.StreamResponse:
        response = web.FileResponse(self._controller_web / "manifest.json")
        response.headers["Content-Type"] = "application/manifest+json"
        response.headers["Cache-Control"] = "no-cache"
        return response

    async def _service_worker(self, request: web.Request) -> web.StreamResponse:
        response = web.FileResponse(self._controller_web / "sw.js")
        response.headers["Content-Type"] = "application/javascript; charset=utf-8"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Service-Worker-Allowed"] = "/"
        return response

    async def _game_asset(self, request: web.Request) -> web.StreamResponse:
        with self._lock:
            game_id = self._game_id
            root = self._game_assets
        if root is None or request.match_info.get("game_id") != game_id:
            raise web.HTTPNotFound()
        tail = request.match_info.get("tail", "")
        if not tail:
            raise web.HTTPNotFound()
        candidate = (root / tail).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            raise web.HTTPNotFound() from None
        if not candidate.is_file() or candidate.stat().st_size > MAX_ASSET_BYTES:
            raise web.HTTPNotFound()
        content_type = ASSET_TYPES.get(candidate.suffix.lower())
        if content_type is None:
            raise web.HTTPNotFound()
        response = web.FileResponse(candidate)
        response.headers["Content-Type"] = content_type
        response.headers["Cache-Control"] = "private, max-age=60"
        return response

    async def _photo(self, request: web.Request) -> web.StreamResponse:
        token = request.headers.get("X-Toxinator-Token", "")
        if token != self._token:
            raise web.HTTPUnauthorized(text="bad token")
        try:
            slot = int(request.query.get("slot", "0"))
        except ValueError:
            slot = 0
        if slot < 0 or slot >= self._registry.max_slots:
            raise web.HTTPBadRequest(text="bad slot")
        content_type = request.headers.get("Content-Type", "").split(";")[0].strip()
        extension = PHOTO_TYPES.get(content_type)
        if extension is None:
            raise web.HTTPUnsupportedMediaType(text="expected image/jpeg or image/png")
        data = await request.read()
        if len(data) > MAX_PHOTO_BYTES:
            raise web.HTTPRequestEntityTooLarge(max_size=MAX_PHOTO_BYTES, actual_size=len(data))
        if len(data) < MIN_PHOTO_BYTES:
            raise web.HTTPBadRequest(text="photo too small")
        photo_id = f"{int(time.time() * 1000)}-{slot}.{extension}"
        with self._lock:
            self._photos[slot] = {
                "id": photo_id,
                "data": data,
                "content_type": content_type,
                "timestamp": time.monotonic(),
            }
        logger.info("phone photo slot=%s bytes=%s", slot, len(data))
        return web.json_response({"id": photo_id, "bytes": len(data)}, status=201)

    def _html_response(self, name: str, *, cache: str) -> web.StreamResponse:
        response = web.FileResponse(self._controller_web / name)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.headers["Cache-Control"] = cache
        response.headers["Permissions-Policy"] = "camera=(self)"
        return response

    async def _websocket(self, request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse(heartbeat=20.0, max_msg_size=1_048_576)
        await ws.prepare(request)

        try:
            hello = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
        except TimeoutError, ValueError, TypeError, web.HTTPException:
            await ws.close(code=1008, message=b"hello required")
            return ws

        if (
            not isinstance(hello, dict)
            or hello.get("type") != "hello"
            or hello.get("token") != self._token
        ):
            await ws.send_json({"type": "error", "code": "bad-token"})
            await ws.close(code=1008, message=b"bad token")
            return ws

        protocol = hello.get("protocol", PROTOCOL)
        if protocol != PROTOCOL:
            await ws.send_json({"type": "error", "code": "bad-protocol"})
            await ws.close(code=1008, message=b"bad protocol")
            return ws

        connection = self._registry.join(
            remote=request.remote or "",
            name=str(hello.get("name", ""))[:80],
        )
        if connection is None:
            await ws.send_json({"type": "error", "code": "full"})
            await ws.close(code=1013, message=b"full")
            return ws

        await ws.send_json(
            {
                "type": "welcome",
                "protocol": PROTOCOL,
                "slot": connection.slot,
                "controller_id": connection.controller_id,
            }
        )
        logger.info(
            "phone slot %s conectado (%s)",
            connection.slot,
            request.remote or "?",
        )
        with self._lock:
            self._clients[ws] = connection.slot
            mode = self._mode
            controller = self._controller
            panel = self._panel_payload_locked()
        await ws.send_json({"type": "mode", "mode": mode})
        await ws.send_json({"type": "controller", "profile": controller})
        await ws.send_json({"type": "panel", "panel": panel})

        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    try:
                        payload = json.loads(message.data)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(payload, dict):
                        continue
                    kind = payload.get("type")
                    if kind == "state":
                        self._registry.update_state(connection.slot, payload)
                    elif kind == "calibrate":
                        self._registry.calibrate(connection.slot)
                        logger.info("phone slot %s calibrado", connection.slot)
                        await ws.send_json({"type": "calibrated"})
                    elif kind == "ping":
                        await ws.send_json({"type": "pong", "t": payload.get("t")})
                elif message.type == WSMsgType.ERROR:
                    break
        finally:
            with self._lock:
                self._clients.pop(ws, None)
            self._registry.leave(connection.slot)
            logger.info("phone slot %s desconectado", connection.slot)

        return ws
