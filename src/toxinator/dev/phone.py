from __future__ import annotations

import secrets
import time
from argparse import Namespace
from pathlib import Path

import segno
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import AmbientLight, CardMaker, DirectionalLight, TextNode
from platformdirs import user_cache_dir, user_data_dir

from toxinator.input.gestures import ThrowDetector
from toxinator.input.hub import InputHub
from toxinator.input.phone.server import PhoneServer


class PhonePrototype(ShowBase):
    """Minimal 3D view driven by the Android phone controller."""

    def __init__(self, args: Namespace) -> None:
        super().__init__()

        self.args = args
        self.hub = InputHub()
        self.detector = ThrowDetector()
        self.token = secrets.token_urlsafe(8)
        self._throw_count = 0

        cache_dir = Path(user_cache_dir("toxinator")) / "prototype"
        cache_dir.mkdir(parents=True, exist_ok=True)
        trace_dir = Path(user_data_dir("toxinator")) / "traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / f"phone-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"

        public_url = args.url or f"http://localhost:{args.port}"
        self.server = PhoneServer(
            self.hub,
            self._web_dir(),
            host=args.host,
            port=args.port,
            token=self.token,
            public_url=public_url,
            trace_path=trace_path,
            tls_cert=args.tls_cert,
            tls_key=args.tls_key,
        )
        self.server.start()

        self.setBackgroundColor(0.04, 0.05, 0.08, 1)
        self.disableMouse()
        self.camera.setPos(0, -9, 4)
        self.camera.lookAt(0, 0, 0)
        self._setup_scene()
        self._setup_qr(cache_dir)
        self._setup_text(trace_path)
        self.taskMgr.add(self._update, "phone-update", sort=-100)
        self.accept("escape", self._quit)

    def _web_dir(self) -> Path:
        return Path(__file__).resolve().parents[3] / "controller-web"

    def _setup_scene(self) -> None:
        ground_maker = CardMaker("ground")
        ground_maker.setFrame(-3, 3, -10, 2)
        ground = self.render.attachNewNode(ground_maker.generate())
        ground.setP(-90)
        ground.setZ(-1.0)
        ground.setColor(0.08, 0.16, 0.12, 1)

        self.paddle = self.loader.loadModel("models/box")
        self.paddle.reparentTo(self.render)
        self.paddle.setScale(0.35, 0.12, 0.9)
        self.paddle.setPos(0, 0, 0)
        self.paddle.setColor(0.2, 0.8, 0.9, 1)

        ambient = AmbientLight("ambient")
        ambient.setColor((0.55, 0.55, 0.65, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor((0.85, 0.9, 1.0, 1))
        sun_node = self.render.attachNewNode(sun)
        sun_node.setHpr(45, -45, 0)
        self.render.setLight(sun_node)

    def _setup_qr(self, cache_dir: Path) -> None:
        qr_path = cache_dir / "qr.png"
        segno.make(self.server.url).save(qr_path, scale=6, border=2)
        self.qr = OnscreenImage(image=str(qr_path), pos=(-0.72, 0, 0.38), scale=0.28)

    def _setup_text(self, trace_path: Path) -> None:
        self.url_text = OnscreenText(
            text=f"Phone: {self.server.url}",
            pos=(-1.32, 0.92),
            scale=0.04,
            fg=(0.9, 0.95, 1, 1),
            align=TextNode.ALeft,
        )
        self.status_text = OnscreenText(
            text="Waiting for phone...",
            pos=(-1.32, 0.85),
            scale=0.05,
            fg=(1, 0.8, 0.2, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.data_text = OnscreenText(
            text="",
            pos=(-1.32, 0.70),
            scale=0.038,
            fg=(0.8, 0.9, 1, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.throw_text = OnscreenText(
            text="Throw: -",
            pos=(-1.32, 0.12),
            scale=0.055,
            fg=(0.4, 1, 0.6, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.help_text = OnscreenText(
            text="1) adb reverse tcp:8443 tcp:8443   2) scan QR   3) hold THROW and swing",
            pos=(-1.32, -0.88),
            scale=0.034,
            fg=(0.7, 0.75, 0.85, 1),
            align=TextNode.ALeft,
        )
        self.trace_text = OnscreenText(
            text=f"Trace: {trace_path}",
            pos=(-1.32, -0.94),
            scale=0.028,
            fg=(0.45, 0.5, 0.6, 1),
            align=TextNode.ALeft,
        )

    def _update(self, task: Task) -> int:
        frame = self.hub.latest(1)
        if frame is None:
            self.status_text.setText("Waiting for phone...")
            return Task.cont

        age_ms = max(0.0, time.monotonic() - frame.timestamp) * 1000
        self.status_text.setText(f"Connected - age {age_ms:.0f} ms")

        raw = frame.raw
        alpha = float(raw.get("alpha", 0.0))
        beta = float(raw.get("beta", 0.0))
        gamma = float(raw.get("gamma", 0.0))
        # Phone Euler axes: alpha = Z (yaw), beta = X (pitch), gamma = Y (roll).
        # Map them directly so forward/back tilt pitches instead of spinning.
        self.paddle.setHpr(alpha, beta, gamma)

        accel = frame.accel
        gyro = frame.gyro
        self.data_text.setText(
            f"beta {beta:6.1f}   gamma {gamma:6.1f}   alpha {alpha:6.1f}\n"
            f"accel {accel.x if accel else 0.0:5.2f} {accel.y if accel else 0.0:5.2f} "
            f"{accel.z if accel else 0.0:5.2f} g\n"
            f"gyro  {gyro.x if gyro else 0.0:6.1f} {gyro.y if gyro else 0.0:6.1f} "
            f"{gyro.z if gyro else 0.0:6.1f} deg/s"
        )

        event = self.detector.update(frame)
        if event is not None:
            self._throw_count += 1
            self.throw_text.setText(
                f"Throw #{self._throw_count}: speed {event.speed:.2f} g, "
                f"spin {event.spin:6.1f}, conf {event.confidence:.2f}"
            )
            self.paddle.setColor(1.0, 0.45, 0.15, 1)
            self.taskMgr.doMethodLater(0.35, self._reset_paddle_color, "reset-paddle")

        return Task.cont

    def _reset_paddle_color(self, task: Task) -> int:
        self.paddle.setColor(0.2, 0.8, 0.9, 1)
        return Task.done

    def _quit(self) -> None:
        self.server.stop()
        self.userExit()
