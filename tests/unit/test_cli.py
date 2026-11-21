from __future__ import annotations

from pathlib import Path

import pytest

from toxinator.cli import build_parser, main


def test_http_is_the_default_and_https_is_opt_in() -> None:
    parser = build_parser()

    args = parser.parse_args(["launcher"])
    assert args.https is False
    assert args.cert is None
    assert args.key is None

    args = parser.parse_args(["launcher", "--https"])
    assert args.https is True


def test_cert_and_key_are_accepted_for_play_and_phone() -> None:
    parser = build_parser()

    for command in (["play"], ["dev", "phone"]):
        args = parser.parse_args([*command, "--cert", "cert.pem", "--key", "key.pem"])
        assert str(args.cert) == "cert.pem"
        assert str(args.key) == "key.pem"


def test_new_accepts_an_id_directory_and_name() -> None:
    parser = build_parser()

    args = parser.parse_args(["new", "mi-juego"])
    assert args.game == "mi-juego"
    assert args.dir is None
    assert args.name is None

    args = parser.parse_args(["new", "mi-juego", "--dir", "projects", "--name", "Mi Juego"])
    assert str(args.dir) == "projects"
    assert args.name == "Mi Juego"


def test_install_defaults_to_the_current_directory() -> None:
    parser = build_parser()

    args = parser.parse_args(["install"])
    assert str(args.path) == "."
    assert args.force is False

    args = parser.parse_args(["install", "mi-juego", "--force"])
    assert str(args.path) == "mi-juego"
    assert args.force is True


def test_new_then_install_via_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOXINATOR_GAMES_DIR", str(tmp_path / "games"))

    assert main(["new", "mi-juego"]) == 0
    assert (tmp_path / "mi-juego" / "src" / "mi_juego" / "manifest.toml").is_file()

    assert main(["install", "mi-juego"]) == 0
    link = tmp_path / "games" / "mi-juego"
    assert link.is_symlink()
    assert link.resolve() == (tmp_path / "mi-juego").resolve()

    output = capsys.readouterr().out
    assert "Juego creado" in output
    assert "Juego instalado" in output
    assert ".opencode/skills/toxinator-game-dev" in output


def test_keyboard_flags_are_available_for_launcher_play_and_phone() -> None:
    parser = build_parser()

    for command in (["launcher"], ["play"], ["dev", "phone"]):
        args = parser.parse_args(command)
        assert args.no_keyboard is False
        assert args.keyboard_slot == 4

        args = parser.parse_args([*command, "--no-keyboard", "--keyboard-slot", "6"])
        assert args.no_keyboard is True
        assert args.keyboard_slot == 6


def test_cloudflare_flag_is_available_for_launcher_play_and_phone() -> None:
    parser = build_parser()

    for command in (
        ["launcher", "--cloudflare"],
        ["play", "--cloudflare"],
        ["dev", "phone", "--cloudflare"],
    ):
        args = parser.parse_args(command)
        assert args.cloudflare is True


def test_fps_overlay_flag_is_available_for_launcher_play_and_phone() -> None:
    parser = build_parser()

    for command in (["launcher"], ["play"], ["dev", "phone"]):
        args = parser.parse_args(command)
        assert args.fps is False

        args = parser.parse_args([*command, "--fps"])
        assert args.fps is True
