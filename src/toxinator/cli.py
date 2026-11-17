"""``toxinator`` command line."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from toxinator import __version__


def _add_cert_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cert",
        type=Path,
        default=None,
        help="certificado TLS PEM (por ejemplo, el de mkcert)",
    )
    parser.add_argument(
        "--key",
        type=Path,
        default=None,
        help="clave privada TLS PEM que acompaña a --cert",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toxinator",
        description="Toxinator 3 game console",
    )
    parser.add_argument("--version", action="version", version=__version__)

    subparsers = parser.add_subparsers(dest="command", required=False)

    dev = subparsers.add_parser("dev", help="development commands")
    dev_sub = dev.add_subparsers(dest="dev_command", required=True)

    phone = dev_sub.add_parser("phone", help="phone controller + minimal 3D scene")
    phone.add_argument(
        "--host",
        default=None,
        help="LAN IP or hostname to put in the QR (default: auto-detect)",
    )
    phone.add_argument("--port", type=int, default=8443, help="HTTPS/WSS port")
    phone.add_argument("--token", default=None, help="fixed session token (dev)")
    _add_cert_arguments(phone)
    phone.add_argument(
        "--demo",
        action="store_true",
        help="add a synthetic phone on P1 (no real phone needed)",
    )
    phone.add_argument(
        "--headless",
        action="store_true",
        help="run the server and print input without opening a window",
    )
    phone.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="stop after N seconds",
    )
    phone.add_argument(
        "--offscreen",
        action="store_true",
        help="render with an offscreen buffer (for screenshots/CI)",
    )
    phone.add_argument(
        "--screenshot",
        type=Path,
        default=None,
        help="save a screenshot and exit",
    )
    phone.add_argument(
        "--screenshot-after",
        type=float,
        default=2.0,
        help="seconds before the screenshot",
    )

    launcher = subparsers.add_parser("launcher", help="open the LIGA launcher")
    launcher.add_argument("--host", default=None, help="LAN IP or hostname for the QR")
    launcher.add_argument("--port", type=int, default=8443, help="HTTPS/WSS port")
    launcher.add_argument("--token", default=None, help="fixed session token (dev)")
    _add_cert_arguments(launcher)
    launcher.add_argument(
        "--demo",
        action="store_true",
        help="add a synthetic phone on P1 (no real phone needed)",
    )
    launcher.add_argument("--seconds", type=float, default=None, help="stop after N seconds")
    launcher.add_argument("--offscreen", action="store_true", help="render offscreen")
    launcher.add_argument(
        "--screenshot", type=Path, default=None, help="save a screenshot and exit"
    )
    launcher.add_argument(
        "--screenshot-after",
        type=float,
        default=3.0,
        help="seconds before the screenshot",
    )

    play = subparsers.add_parser("play", help="play a game with the phone controller")
    play.add_argument("game", nargs="?", default="maldito-pino")
    play.add_argument("--host", default=None, help="LAN IP or hostname for the QR")
    play.add_argument("--port", type=int, default=8443, help="HTTPS/WSS port")
    play.add_argument("--token", default=None, help="fixed session token (dev)")
    _add_cert_arguments(play)
    play.add_argument(
        "--demo",
        action="store_true",
        help="add a synthetic phone on P1 (no real phone needed)",
    )
    play.add_argument("--seconds", type=float, default=None, help="stop after N seconds")
    play.add_argument("--offscreen", action="store_true", help="render offscreen")
    play.add_argument("--screenshot", type=Path, default=None, help="save a screenshot and exit")
    play.add_argument(
        "--screenshot-after",
        type=float,
        default=3.0,
        help="seconds before the screenshot",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["launcher"])

    if args.command == "launcher":
        from toxinator.dev.launcher import run_launcher

        try:
            run_launcher(
                host=args.host,
                port=args.port,
                token=args.token,
                demo=args.demo,
                seconds=args.seconds,
                offscreen=args.offscreen,
                screenshot=args.screenshot,
                screenshot_after=args.screenshot_after,
                cert=args.cert,
                key=args.key,
            )
        except KeyboardInterrupt:
            return 130
        except (OSError, RuntimeError) as error:
            parser.exit(1, f"toxinator: {error}\n")
    elif args.command == "dev" and args.dev_command == "phone":
        from toxinator.dev.phone import run_phone_dev

        try:
            run_phone_dev(
                host=args.host,
                port=args.port,
                token=args.token,
                demo=args.demo,
                headless=args.headless,
                seconds=args.seconds,
                offscreen=args.offscreen,
                screenshot=args.screenshot,
                screenshot_after=args.screenshot_after,
                cert=args.cert,
                key=args.key,
            )
        except KeyboardInterrupt:
            return 130
        except (OSError, RuntimeError) as error:
            parser.exit(1, f"toxinator: {error}\n")
    elif args.command == "play":
        from toxinator.dev.play import run_play

        try:
            run_play(
                game_id=args.game,
                host=args.host,
                port=args.port,
                token=args.token,
                demo=args.demo,
                seconds=args.seconds,
                offscreen=args.offscreen,
                screenshot=args.screenshot,
                screenshot_after=args.screenshot_after,
                cert=args.cert,
                key=args.key,
            )
        except KeyboardInterrupt:
            return 130
        except (OSError, RuntimeError) as error:
            parser.exit(1, f"toxinator: {error}\n")
    return 0
