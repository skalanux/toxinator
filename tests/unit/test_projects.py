from __future__ import annotations

from pathlib import Path

import pytest

from toxinator.api.game import API_VERSION, load_manifest
from toxinator.core.external_games import discover_external_games
from toxinator.dev.projects import (
    GameProjectError,
    create_game_project,
    default_title,
    game_id_to_module,
    install_game_project,
    module_to_class,
)


def _write_minimal_game(root: Path, module: str, game_id: str) -> Path:
    package = root / "src" / module
    package.mkdir(parents=True)
    package.joinpath("manifest.toml").write_text(
        f"""
id = "{game_id}"
name = "Minimal"
version = "0.1.0"
requires_api = "0.2"
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


def test_creates_skeleton_with_manifest_package_and_readme(tmp_path: Path) -> None:
    project = create_game_project("mi-juego", tmp_path, title="Mi Juego")

    root = tmp_path / "mi-juego"
    assert project.root == root
    assert project.game_id == "mi-juego"
    assert project.module == "mi_juego"

    manifest = load_manifest(root / "src" / "mi_juego" / "manifest.toml")
    assert manifest.id == "mi-juego"
    assert manifest.name == "Mi Juego"
    assert manifest.requires_api == API_VERSION

    init = root.joinpath("src", "mi_juego", "__init__.py").read_text(encoding="utf-8")
    assert "from .game import MiJuego" in init
    assert "def create_game(manifest: GameManifest) -> Game:" in init

    game = root.joinpath("src", "mi_juego", "game.py").read_text(encoding="utf-8")
    assert "class MiJuego:" in game
    assert "MI JUEGO" in game
    assert "ctx.input_state.primary_frame()" in game
    assert 'frame.button("cross")' in game

    pyproject = root.joinpath("pyproject.toml").read_text(encoding="utf-8")
    assert 'packages = ["src/mi_juego"]' in pyproject
    assert root.joinpath("README.md").is_file()


def test_copies_the_game_development_skill(tmp_path: Path) -> None:
    project = create_game_project("mi-juego", tmp_path)

    skill = project.root / ".opencode" / "skills" / "toxinator-game-dev"
    assert skill.joinpath("SKILL.md").is_file()
    assert skill.joinpath("references", "contract-and-lifecycle.md").is_file()
    assert "toxinator-game-dev" in project.root.joinpath("README.md").read_text(encoding="utf-8")


def test_default_title_and_names_are_derived_from_the_id(tmp_path: Path) -> None:
    parent = tmp_path / "games"
    parent.mkdir()
    project = create_game_project("super-kart_2", parent)

    manifest = load_manifest(project.root / "src" / "super_kart_2" / "manifest.toml")
    assert manifest.name == "Super Kart 2"
    assert "class SuperKart2:" in project.root.joinpath("src", "super_kart_2", "game.py").read_text(
        encoding="utf-8"
    )


def test_title_with_quotes_is_escaped_in_the_manifest(tmp_path: Path) -> None:
    project = create_game_project("quote-game", tmp_path, title='El "juego"')

    manifest = load_manifest(project.root / "src" / "quote_game" / "manifest.toml")
    assert manifest.name == 'El "juego"'
    assert 'El "juego"' in manifest.description


def test_accepts_an_empty_target_directory(tmp_path: Path) -> None:
    (tmp_path / "mi-juego").mkdir()

    project = create_game_project("mi-juego", tmp_path)

    assert project.root.joinpath("src", "mi_juego", "manifest.toml").is_file()


def test_refuses_to_write_into_a_non_empty_directory(tmp_path: Path) -> None:
    target = tmp_path / "mi-juego"
    target.mkdir()
    target.joinpath("notes.txt").write_text("propio", encoding="utf-8")

    with pytest.raises(GameProjectError):
        create_game_project("mi-juego", tmp_path)

    assert target.joinpath("notes.txt").read_text(encoding="utf-8") == "propio"


@pytest.mark.parametrize("game_id", ["", "Mi Juego", "1game", "-game", "game!", ".hidden"])
def test_rejects_invalid_ids(game_id: str, tmp_path: Path) -> None:
    with pytest.raises(GameProjectError):
        create_game_project(game_id, tmp_path)


def test_refuses_a_missing_parent_directory(tmp_path: Path) -> None:
    with pytest.raises(GameProjectError):
        create_game_project("mi-juego", tmp_path / "missing")


def test_helpers_convert_ids_modules_and_classes() -> None:
    assert game_id_to_module("mi-juego_2") == "mi_juego_2"
    assert module_to_class("mi_juego_2") == "MiJuego2"
    assert default_title("mi-juego_2") == "Mi Juego 2"


def test_install_links_the_game_into_the_games_directory(tmp_path: Path) -> None:
    source = tmp_path / "projects" / "my-game"
    _write_minimal_game(source, "tox_minimal", "minimal-game")
    games = tmp_path / "games"

    link = install_game_project(source, games_root=games)

    assert link == games / "minimal-game"
    assert link.is_symlink()
    assert link.resolve() == source.resolve()
    discovered = discover_external_games(games)
    assert [game.manifest.id for game in discovered] == ["minimal-game"]


def test_install_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "projects" / "my-game"
    _write_minimal_game(source, "tox_idempotent", "idempotent-game")
    games = tmp_path / "games"

    first = install_game_project(source, games_root=games)
    second = install_game_project(source, games_root=games)

    assert first == second
    assert first.is_symlink()


def test_install_replaces_a_symlink_only_with_force(tmp_path: Path) -> None:
    first_source = tmp_path / "one" / "my-game"
    _write_minimal_game(first_source, "tox_first", "shared-game")
    second_source = tmp_path / "two" / "my-game"
    _write_minimal_game(second_source, "tox_second", "shared-game")
    games = tmp_path / "games"

    install_game_project(first_source, games_root=games)

    with pytest.raises(GameProjectError):
        install_game_project(second_source, games_root=games)

    link = install_game_project(second_source, games_root=games, force=True)
    assert link.resolve() == second_source.resolve()


def test_install_never_replaces_a_real_directory(tmp_path: Path) -> None:
    source = tmp_path / "projects" / "my-game"
    _write_minimal_game(source, "tox_realdir", "real-dir-game")
    games = tmp_path / "games"
    existing = games / "real-dir-game"
    existing.mkdir(parents=True)
    existing.joinpath("keep.txt").write_text("no tocar", encoding="utf-8")

    with pytest.raises(GameProjectError):
        install_game_project(source, games_root=games, force=True)

    assert existing.joinpath("keep.txt").is_file()
    assert not existing.is_symlink()


def test_install_is_a_noop_when_the_game_already_lives_there(tmp_path: Path) -> None:
    games = tmp_path / "games"
    source = games / "already-there"
    _write_minimal_game(source, "tox_already", "already-there")

    link = install_game_project(source, games_root=games)

    assert link == source
    assert not link.is_symlink()


def test_install_requires_a_game_manifest(tmp_path: Path) -> None:
    source = tmp_path / "not-a-game"
    source.mkdir()

    with pytest.raises(GameProjectError):
        install_game_project(source, games_root=tmp_path / "games")


def test_install_rejects_ambiguous_manifests(tmp_path: Path) -> None:
    source = tmp_path / "ambiguous"
    _write_minimal_game(source, "tox_a", "game-a")
    _write_minimal_game(source, "tox_b", "game-b")

    with pytest.raises(GameProjectError):
        install_game_project(source, games_root=tmp_path / "games")
