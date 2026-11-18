from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from toxinator.core.external_games import (
    GAMES_DIR_ENV,
    discover_external_games,
    external_entries,
    find_external_game,
    games_dir,
)


def _write_game(root: Path, module: str, game_id: str) -> Path:
    package = root / "my-game" / "src" / module
    package.mkdir(parents=True)
    package.joinpath("manifest.toml").write_text(
        f"""
id = "{game_id}"
name = "External Test"
version = "0.1.0"
requires_api = "0.1"
description = "Juego de prueba"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    package.joinpath("__init__.py").write_text(
        """
class DummyGame:
    def __init__(self, manifest):
        self.manifest = manifest

    def start(self, ctx):
        pass

    def update(self, dt):
        pass

    def stop(self):
        pass


def create_game(manifest):
    return DummyGame(manifest)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return package


def test_discovers_external_game_with_factory(tmp_path: Path) -> None:
    module = f"tox_ext_{uuid4().hex}"
    package = _write_game(tmp_path, module, "external-test")

    games = discover_external_games(tmp_path)

    assert len(games) == 1
    assert games[0].manifest.id == "external-test"
    assert games[0].path == package / "manifest.toml"
    game = games[0].instantiate()
    assert game.manifest.id == "external-test"


def test_find_external_game_by_manifest_id(tmp_path: Path) -> None:
    module = f"tox_ext_{uuid4().hex}"
    _write_game(tmp_path, module, "external-find")

    found = find_external_game("external-find", tmp_path)
    assert found is not None
    assert found.manifest.id == "external-find"
    assert find_external_game("missing", tmp_path) is None


def test_skips_templates_and_packages_without_factory(tmp_path: Path) -> None:
    _write_game(tmp_path / "_template", f"tox_ext_{uuid4().hex}", "template-game")
    module = f"tox_ext_{uuid4().hex}"
    broken = tmp_path / "broken" / "src" / module
    broken.mkdir(parents=True)
    broken.joinpath("manifest.toml").write_text(
        'id = "broken"\nname = "Broken"\nversion = "0.1.0"\n'
        'requires_api = "0.1"\n',
        encoding="utf-8",
    )
    broken.joinpath("__init__.py").write_text("", encoding="utf-8")

    assert discover_external_games(tmp_path) == []


def test_games_dir_can_be_overridden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(GAMES_DIR_ENV, str(tmp_path))
    assert games_dir() == tmp_path


def test_external_game_becomes_launcher_entry(tmp_path: Path) -> None:
    module = f"tox_ext_{uuid4().hex}"
    _write_game(tmp_path, module, "external-entry")

    entries = external_entries(tmp_path)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.id == "external-entry"
    assert entry.title == "External Test"
    assert entry.subtitle == "JUEGO EXTERNO"
    assert entry.rank == "EX"
    assert entry.installed
    assert entry.manifest is not None
    assert entry.instantiate().manifest.id == "external-entry"
