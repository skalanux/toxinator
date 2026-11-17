from __future__ import annotations

import asyncio
import json
import ssl
import threading
import time
from pathlib import Path
from typing import Any

from aiohttp import WSMsgType, web

from toxinator.api import ControllerFrame, Quat, TouchPoint, Vec3
from toxinator.input.hub import InputHub


class PhoneServer:
    """Serve the controller PWA and receive phone state over WebSocket.

    The server runs in a background thread with its own asyncio loop. The game
    loop reads the latest frame from the thread-safe InputHub.
    """

    def __init__(
        self,
        hub: InputHub,
        web_dir: Path,
        *,
        host: str = "127.0.0.1",
        port: int = 8443,
        token: str,
        public_url: str | None = None,
        trace_path: Path | None = None,
        tls_cert: Path | None = None,
        tls_key: Path | None = None,
    ) -> None:
        self.hub = hub
        self.web_dir = web_dir
        self.host = host
        self.port = port
        self.token = token
        self.base_url = (public_url or f"http://localhost:{port}").rstrip("/")
        self.trace_path = trace_path
        self.tls_cert = tls_cert
        self.tls_key = tls_key

        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._error: BaseException | None = None
        self._trace_file: Any = None

    @property
    def url(self) -> str:
        return f"{self.base_url}/?token={self.token}"

    def start(self) -> None:
        self._thread = threading.Thread(target=self._thread_main, name="phone-server", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=8):
            detail = f": {self._error!r}" if self._error else ""
            raise RuntimeError(f"phone server did not start{detail}")
        print(f"[phone] controller: {self.url}")
        print("[phone] if using USB: adb reverse tcp:8443 tcp:8443")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._loop is not None
        ):
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=1)

    def _thread_main(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run())
        except BaseException as exc:  # noqa: BLE001 - surface startup errors
            self._error = exc
        finally:
            self._loop.close()

    async def _run(self) -> None:
        if not (self.web_dir / "index.html").exists():
            raise FileNotFoundError(f"controller web dir not found: {self.web_dir}")

        if self.trace_path is not None:
            self.trace_path.parent.mkdir(parents=True, exist_ok=True)
            self._trace_file = self.trace_path.open("a", encoding="utf-8")

        app = web.Application()
        app.router.add_get("/", self._index)
        app.router.add_get("/ws", self._ws)
        app.router.add_static("/static/", self.web_dir)

        runner = web.AppRunner(app)
        await runner.setup()

        ssl_context = None
        if self.tls_cert is not None and self.tls_key is not None:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(str(self.tls_cert), str(self.tls_key))

        site = web.TCPSite(runner, self.host, self.port, ssl_context=ssl_context)
        await site.start()
        self._ready.set()

        try:
            while not self._stop.is_set():
                await asyncio.sleep(0.1)
        finally:
            await runner.cleanup()
            if self._trace_file is not None:
                self._trace_file.close()
                self._trace_file = None

    async def _index(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(self.web_dir / "index.html")

    async def _ws(self, request: web.Request) -> web.WebSocketResponse:
        if request.query.get("token") != self.token:
            raise web.HTTPForbidden(text="bad token")

        ws = web.WebSocketResponse(heartbeat=5.0)
        await ws.prepare(request)
        async for message in ws:
            if message.type == WSMsgType.TEXT:
                self._handle_text(message.data)
            elif message.type == WSMsgType.ERROR:
                break
        return ws

    def _handle_text(self, data: str) -> None:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return

        now = time.monotonic()
        accel = self._vec3(payload.get("accel"))
        gyro = self._vec3(payload.get("gyro"))
        orientation = self._quat(payload.get("orientation"))
        euler = payload.get("orientation_euler")
        if not isinstance(euler, dict):
            euler = {}
        buttons = payload.get("buttons")
        if not isinstance(buttons, dict):
            buttons = {}
        touches = payload.get("touches")
        if not isinstance(touches, list):
            touches = []

        frame = ControllerFrame(
            timestamp=now,
            controller_id=str(payload.get("id", "phone")),
            slot=int(payload.get("slot", 1)),
            connected=True,
            buttons=frozenset(str(name) for name, pressed in buttons.items() if pressed),
            accel=accel,
            gyro=gyro,
            orientation=orientation,
            touch=tuple(
                TouchPoint(
                    id=int(touch.get("id", 0)),
                    x=float(touch.get("x", 0.0)),
                    y=float(touch.get("y", 0.0)),
                )
                for touch in touches
                if isinstance(touch, dict)
            ),
            seq=int(payload["seq"]) if isinstance(payload.get("seq"), int) else None,
            raw={
                "alpha": float(euler.get("alpha", 0.0)),
                "beta": float(euler.get("beta", 0.0)),
                "gamma": float(euler.get("gamma", 0.0)),
                "type": payload.get("type"),
            },
        )
        self.hub.update(frame)
        self._write_trace(payload, now)

    def _write_trace(self, payload: dict[str, Any], now: float) -> None:
        if self._trace_file is None:
            return
        record = {"t": now, **payload}
        self._trace_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._trace_file.flush()

    @staticmethod
    def _vec3(value: Any) -> Vec3 | None:
        if not isinstance(value, list) or len(value) != 3:
            return None
        try:
            return Vec3(float(value[0]), float(value[1]), float(value[2]))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _quat(value: Any) -> Quat | None:
        if not isinstance(value, list) or len(value) != 4:
            return None
        try:
            return Quat(float(value[0]), float(value[1]), float(value[2]), float(value[3]))
        except (TypeError, ValueError):
            return None
