"""Temporary Cloudflare Quick Tunnel for valid HTTPS without touching a CA."""

from __future__ import annotations

import logging
import os
import re
import shutil
import signal
import subprocess
import threading
from collections import deque

logger = logging.getLogger(__name__)

CLOUDFLARE_URL_RE = re.compile(r"https://[-a-z0-9]+\.trycloudflare\.com", re.IGNORECASE)
DEFAULT_TIMEOUT = 30.0


class CloudflareTunnelError(RuntimeError):
    """The quick tunnel could not be started or did not return a URL."""


class CloudflareQuickTunnel:
    """Run ``cloudflared tunnel --url`` and expose its public HTTPS URL."""

    def __init__(
        self,
        port: int,
        *,
        executable: str = "cloudflared",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._port = port
        self._executable = executable
        self._timeout = timeout
        self._process: subprocess.Popen[str] | None = None
        self._reader: threading.Thread | None = None
        self._url: str | None = None
        self._ready = threading.Event()
        self._output: deque[str] = deque(maxlen=40)

    @property
    def url(self) -> str | None:
        return self._url

    def start(self) -> str:
        executable = shutil.which(self._executable)
        if executable is None:
            raise CloudflareTunnelError(
                "no encuentro cloudflared; instalalo con "
                "`sudo pacman -S cloudflared` o quitá --cloudflare"
            )
        self._url = None
        self._ready.clear()
        self._output.clear()
        command = [
            executable,
            "tunnel",
            "--url",
            f"http://127.0.0.1:{self._port}",
            "--no-autoupdate",
        ]
        logger.info("iniciando Cloudflare Quick Tunnel en el puerto %s", self._port)
        try:
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
        except OSError as error:
            raise CloudflareTunnelError(f"no pude iniciar cloudflared: {error}") from error

        self._reader = threading.Thread(
            target=self._read_output,
            name="cloudflared-output",
            daemon=True,
        )
        self._reader.start()
        if not self._ready.wait(self._timeout):
            self.stop()
            raise CloudflareTunnelError(
                "cloudflared no devolvió una URL a tiempo. "
                "Revisá la conexión a internet o corré "
                "`cloudflared tunnel --url http://127.0.0.1:PORT` a mano."
            )
        if self._url is None:
            details = "\n".join(self._output)
            self.stop()
            raise CloudflareTunnelError(
                "cloudflared terminó sin una URL pública."
                + (f"\n{details}" if details else "")
            )
        logger.info("Cloudflare Quick Tunnel: %s", self._url)
        return self._url

    def _read_output(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            self._ready.set()
            return
        try:
            for line in process.stdout:
                text = line.rstrip()
                if not text:
                    continue
                self._output.append(text)
                logger.debug("cloudflared: %s", text)
                if self._url is None:
                    match = CLOUDFLARE_URL_RE.search(text)
                    if match is not None:
                        self._url = match.group(0)
                        self._ready.set()
        except (OSError, ValueError):
            pass
        finally:
            self._ready.set()

    def stop(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                process.kill()
            process.wait(timeout=2.0)
        if self._reader is not None:
            self._reader.join(timeout=2.0)
            self._reader = None
        if process.stdout is not None:
            process.stdout.close()
