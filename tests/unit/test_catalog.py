from __future__ import annotations

import pytest

from toxinator.core.games import find_game, load_catalog


def test_catalog_lists_installed_game_and_future_challenges() -> None:
    entries = load_catalog()
    assert [entry.id for entry in entries] == ["maldito-pino", "kart", "tenis"]

    maldito = entries[0]
    assert maldito.installed
    assert maldito.rank == "A"
    assert maldito.event == "01"
    assert maldito.manifest is not None
    assert maldito.players == (1, 1)

    kart = entries[1]
    assert not kart.installed
    assert kart.event == "02"
    assert kart.players == (1, 4)


def test_find_game_and_unknown_id() -> None:
    assert find_game("maldito-pino").id == "maldito-pino"
    with pytest.raises(RuntimeError):
        find_game("does-not-exist")
