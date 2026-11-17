"""QR image generation for the phone pairing overlay."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import qrcode
from panda3d.core import Texture


def qr_cache_path() -> Path:
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "toxinator" / "phone-qr.png"


def qr_texture(base: Any, url: str, path: Path | None = None) -> Texture:
    """Render a high-contrast QR PNG and load it as a nearest-filter texture."""
    target = path or qr_cache_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    image.save(target)

    texture = base.loader.loadTexture(str(target))
    texture.setMagfilter(Texture.FT_nearest)
    texture.setMinfilter(Texture.FT_nearest)
    return texture
