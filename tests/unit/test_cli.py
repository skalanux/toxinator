from __future__ import annotations

from toxinator.cli import build_parser


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
