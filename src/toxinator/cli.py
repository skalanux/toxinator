"""``toxinator`` command line."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from toxinator import __version__


def _add_cert_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--https",
        action="store_true",
        help=(
            "servir HTTPS/WSS (autofirmado si no pasás --cert/--key); "
            "por defecto usa HTTP/WS sin certificado"
        ),
    )
    parser.add_argument(
        "--cert",
        type=Path,
        default=None,
        help="certificado TLS PEM (por ejemplo, el de mkcert); implica HTTPS",
    )
    parser.add_argument(
        "--key",
        type=Path,
        default=None,
        help="clave privada TLS PEM que acompaña a --cert; implica HTTPS",
    )


def _add_keyboard_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-keyboard",
        action="store_true",
        help="no agregar el simulador de teclado/mouse como mando",
    )
    parser.add_argument(
        "--keyboard-slot",
        type=int,
        default=4,
        help="slot del mando simulado por teclado/mouse (default: 4)",
    )


def _add_fps_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--fps",
        action="store_true",
        help="mostrar overlay de FPS/frametime (F3 lo oculta); útil para medir hardware",
    )


def _add_cloudflare_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cloudflare",
        action="store_true",
        help=(
            "crear un Cloudflare Quick Tunnel HTTPS (requiere cloudflared); "
            "el QR usa la URL pública y no hay que tocar la CA del teléfono"
        ),
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
    _add_cloudflare_argument(phone)
    _add_fps_argument(phone)
    _add_keyboard_arguments(phone)
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

    launcher = subparsers.add_parser("launcher", help="open the Toxinator launcher")
    launcher.add_argument("--host", default=None, help="LAN IP or hostname for the QR")
    launcher.add_argument("--port", type=int, default=8443, help="HTTPS/WSS port")
    launcher.add_argument("--token", default=None, help="fixed session token (dev)")
    _add_cert_arguments(launcher)
    _add_cloudflare_argument(launcher)
    _add_fps_argument(launcher)
    _add_keyboard_arguments(launcher)
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
    _add_cloudflare_argument(play)
    _add_fps_argument(play)
    _add_keyboard_arguments(play)
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

    new = subparsers.add_parser(
        "new",
        help="crear el esqueleto de un juego externo",
    )
    new.add_argument(
        "game",
        help="id del juego (minúsculas, números, '-' o '_'; el módulo usa '_')",
    )
    new.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="directorio donde crear <id> (por defecto, el actual)",
    )
    new.add_argument(
        "--name",
        default=None,
        help="nombre visible del juego (por defecto, derivado del id)",
    )

    install = subparsers.add_parser(
        "install",
        help="instalar un juego externo con un symlink al directorio",
    )
    install.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("."),
        help="directorio del juego con src/<módulo>/manifest.toml (por defecto, el actual)",
    )
    install.add_argument(
        "--force",
        action="store_true",
        help="reemplazar un symlink existente en el directorio de juegos",
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
                https=args.https,
                offscreen=args.offscreen,
                screenshot=args.screenshot,
                screenshot_after=args.screenshot_after,
                keyboard=not args.no_keyboard,
                keyboard_slot=args.keyboard_slot,
                cert=args.cert,
                key=args.key,
                cloudflare=args.cloudflare,
                show_fps=args.fps,
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
                https=args.https,
                offscreen=args.offscreen,
                screenshot=args.screenshot,
                screenshot_after=args.screenshot_after,
                keyboard=not args.no_keyboard,
                keyboard_slot=args.keyboard_slot,
                cert=args.cert,
                key=args.key,
                cloudflare=args.cloudflare,
                show_fps=args.fps,
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
                https=args.https,
                offscreen=args.offscreen,
                screenshot=args.screenshot,
                screenshot_after=args.screenshot_after,
                keyboard=not args.no_keyboard,
                keyboard_slot=args.keyboard_slot,
                cert=args.cert,
                key=args.key,
                cloudflare=args.cloudflare,
                show_fps=args.fps,
            )
        except KeyboardInterrupt:
            return 130
        except (OSError, RuntimeError) as error:
            parser.exit(1, f"toxinator: {error}\n")
    elif args.command == "new":
        from toxinator.dev.projects import SKILL_NAME, create_game_project

        try:
            project = create_game_project(
                args.game,
                args.dir or Path.cwd(),
                title=args.name,
            )
        except (OSError, RuntimeError) as error:
            parser.exit(1, f"toxinator: {error}\n")
        print(f"Juego creado en {project.root}")
        print(f"  id: {project.game_id}   módulo: {project.module}")
        print(f"  skill: .opencode/skills/{SKILL_NAME}/")
        print(f"Siguiente: toxinator install {project.root}")
    elif args.command == "install":
        from toxinator.dev.projects import install_game_project

        try:
            link = install_game_project(args.path, force=args.force)
        except (OSError, RuntimeError) as error:
            parser.exit(1, f"toxinator: {error}\n")
        print(f"Juego instalado en {link}")
        print("Reiniciá el launcher para verlo en la biblioteca.")
    return 0
