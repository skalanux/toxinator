"""HTTP/HTTPS + WebSocket development server for the phone controller."""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from aiohttp import WSMsgType, web

from toxinator.input.phone.registry import PhoneRegistry

logger = logging.getLogger(__name__)


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
        with self._lock:
            self._controller = dict(profile) if profile is not None else None
            controller = self._controller
        self._broadcast({"type": "controller", "profile": controller})

    def send_haptic(self, pattern: int | Sequence[int], slot: int | None = None) -> None:
        """Send a vibration pattern to one phone or all phones."""
        raw = [pattern] if isinstance(pattern, int) else list(pattern)
        values = [
            max(0, min(5000, int(value)))
            for value in raw
            if isinstance(value, (int, float))
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

    async def _serve(self) -> None:
        app = web.Application()
        app.router.add_get("/", self._index)
        app.router.add_get("/manifest.webmanifest", self._manifest)
        app.router.add_get("/sw.js", self._service_worker)
        app.router.add_get("/ws", self._websocket)
        app.router.add_static("/static/", self._controller_web)

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
        except (TimeoutError, ValueError, TypeError, web.HTTPException):
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
                "protocol": 1,
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
        await ws.send_json({"type": "mode", "mode": mode})
        await ws.send_json({"type": "controller", "profile": controller})

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
