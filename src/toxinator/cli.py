from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toxinator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dev = subparsers.add_parser("dev", help="developer commands")
    dev_subparsers = dev.add_subparsers(dest="dev_command", required=True)

    phone = dev_subparsers.add_parser("phone", help="phone-first controller prototype")
    phone.add_argument("--host", default="127.0.0.1", help="bind address (use 0.0.0.0 for LAN)")
    phone.add_argument("--port", type=int, default=8443)
    phone.add_argument(
        "--url",
        default=None,
        help="public URL for the QR (e.g. https://192.168.1.10:8443)",
    )
    phone.add_argument("--tls-cert", type=Path, default=None, help="TLS certificate (PEM)")
    phone.add_argument("--tls-key", type=Path, default=None, help="TLS private key (PEM)")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "dev" and args.dev_command == "phone":
        from toxinator.dev.phone import PhonePrototype

        app = PhonePrototype(args)
        app.run()
        return 0

    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
