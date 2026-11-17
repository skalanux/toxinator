from __future__ import annotations

import pytest
from maldito_pino.scoring import BowlingMatch


def test_perfect_game_scores_300() -> None:
    match = BowlingMatch()
    for _ in range(12):
        match.roll(10)
    assert match.game_over
    assert match.total == 300
    assert match.frame_scores()[9] == 300
    assert match.frame_marks() == ["X"] * 10


def test_all_spares_scores_150() -> None:
    match = BowlingMatch()
    for _ in range(10):
        match.roll(5)
        match.roll(5)
    match.roll(5)
    assert match.game_over
    assert match.total == 150
    assert match.frame_marks() == ["/"] * 10


def test_open_frames_score_90() -> None:
    match = BowlingMatch()
    for _ in range(10):
        match.roll(9)
        match.roll(0)
    assert match.game_over
    assert match.total == 90


def test_tenth_frame_strike_bonus() -> None:
    match = BowlingMatch()
    for _ in range(9):
        match.roll(9)
        match.roll(0)
    match.roll(10)
    match.roll(7)
    match.roll(2)
    assert match.game_over
    assert match.total == 100
    assert match.frames[9] == [10, 7, 2]


def test_tenth_frame_open_ends_game() -> None:
    match = BowlingMatch()
    for _ in range(9):
        match.roll(0)
        match.roll(0)
    match.roll(3)
    match.roll(4)
    assert match.game_over
    assert match.frames[9] == [3, 4]
    assert match.total == 7


def test_tenth_frame_spare_gets_third_ball() -> None:
    match = BowlingMatch()
    for _ in range(9):
        match.roll(0)
        match.roll(0)
    match.roll(3)
    match.roll(7)
    assert not match.game_over
    assert match.current_ball == 3
    match.roll(8)
    assert match.game_over
    assert match.total == 18


def test_frame_and_ball_state() -> None:
    match = BowlingMatch()
    match.roll(10)
    assert match.frame == 1
    assert match.ball == 0
    assert match.standing == 10

    match.roll(5)
    assert match.frame == 1
    assert match.ball == 1
    assert match.standing == 5

    match.roll(3)
    assert match.frame == 2
    assert match.ball == 0
    assert match.standing == 10


def test_clamps_bad_rolls() -> None:
    match = BowlingMatch()
    result = match.roll(99)
    assert result.pins == 10
    assert match.frame == 1


def test_incomplete_frame_has_no_total() -> None:
    match = BowlingMatch()
    match.roll(10)
    assert match.total == 0
    assert match.frame_scores()[0] is None
    assert match.frame_marks()[0] == "X"


def test_roll_after_game_over_raises() -> None:
    match = BowlingMatch()
    for _ in range(12):
        match.roll(10)
    with pytest.raises(RuntimeError):
        match.roll(0)
