"""Terminal announcement and QR for the phone session."""

from __future__ import annotations

import qrcode

from toxinator.dev.session import PhoneSession


def print_qr(url: str) -> None:
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def announce_phone(
    session: PhoneSession,
    *,
    title: str = "TOXINATOR · dev phone",
    demo: bool = False,
    extra: str | None = None,
) -> None:
    print(f"\n{title}\n", flush=True)
    print(f"  URL:   {session.url}", flush=True)
    print("  Wi-Fi: misma red que la consola", flush=True)
    print("  Cert:  aceptá el aviso de certificado autofirmado una vez", flush=True)
    if extra:
        print(f"  {extra}", flush=True)
    if demo:
        print("  Demo:  fuente sintética activa (P1)", flush=True)
    print("\nEscaneá el QR desde el celular:\n", flush=True)
    print_qr(session.url)
    print("\nCtrl+C para salir.\n", flush=True)
