from __future__ import annotations

import asyncio
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from toxinator.dev.server import MAX_PHOTO_BYTES, DevServer
from toxinator.input.phone.registry import PhoneRegistry

WEB = Path(__file__).resolve().parents[2] / "controller-web"
TOKEN = "test-token"


def _server(tmp_path: Path) -> DevServer:
    server = DevServer(
        host="127.0.0.1",
        port=8443,
        controller_web=WEB,
        ssl_context=None,
        token=TOKEN,
        registry=PhoneRegistry(max_slots=4),
    )
    server.set_game_assets("demo", tmp_path)
    return server


def test_photo_upload_validates_token_type_and_size(tmp_path: Path) -> None:
    async def scenario() -> None:
        server = _server(tmp_path)
        async with TestClient(TestServer(server.make_app())) as client:
            unauthorized = await client.post("/api/photo?slot=0", data=b"x" * 20000)
            assert unauthorized.status == 401

            assert server.last_photo(0) is None

            wrong_type = await client.post(
                "/api/photo?slot=0",
                data=b"x" * 20000,
                headers={"X-Toxinator-Token": TOKEN, "Content-Type": "text/plain"},
            )
            assert wrong_type.status == 415

            too_small = await client.post(
                "/api/photo?slot=0",
                data=b"x" * 100,
                headers={
                    "X-Toxinator-Token": TOKEN,
                    "Content-Type": "image/jpeg",
                },
            )
            assert too_small.status == 400

            too_large = await client.post(
                "/api/photo?slot=0",
                data=b"x" * (MAX_PHOTO_BYTES + 1),
                headers={
                    "X-Toxinator-Token": TOKEN,
                    "Content-Type": "image/jpeg",
                },
            )
            assert too_large.status == 413

            ok = await client.post(
                "/api/photo?slot=0",
                data=b"x" * 20000,
                headers={
                    "X-Toxinator-Token": TOKEN,
                    "Content-Type": "image/jpeg",
                },
            )
            assert ok.status == 201
            payload = await ok.json()
            assert payload["bytes"] == 20000
            stored = server.last_photo(0)
            assert stored is not None
            assert stored[1] == b"x" * 20000

    asyncio.run(scenario())


def test_game_assets_are_served_only_from_the_active_game(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "mapa.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    async def scenario() -> None:
        server = _server(tmp_path)
        async with TestClient(TestServer(server.make_app())) as client:
            ok = await client.get("/game-assets/demo/assets/mapa.png")
            assert ok.status == 200
            assert ok.headers["Content-Type"] == "image/png"

            other = await client.get("/game-assets/otro/assets/mapa.png")
            assert other.status == 404

            traversal = await client.get("/game-assets/demo/%2e%2e/secreto.png")
            assert traversal.status == 404

    asyncio.run(scenario())
