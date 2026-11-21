from __future__ import annotations

import pytest

from toxinator.dev.fps import FrameStats


def test_fps_uses_the_mean_frame_time() -> None:
    stats = FrameStats(window_seconds=10.0)
    for _ in range(60):
        stats.add(1.0 / 60.0)

    assert stats.samples == 60
    assert stats.fps() == pytest.approx(60.0)
    assert stats.mean_ms() == pytest.approx(1000.0 / 60.0)
    assert stats.worst_ms() == pytest.approx(1000.0 / 60.0)


def test_window_discards_old_frames() -> None:
    stats = FrameStats(window_seconds=1.0)
    for _ in range(120):
        stats.add(0.02)

    assert stats.samples <= 52
    assert stats.fps() == pytest.approx(50.0, abs=0.1)


def test_worst_frame_survives_a_short_stutter() -> None:
    stats = FrameStats(window_seconds=10.0)
    stats.add(1.0 / 60.0)
    stats.add(0.1)

    assert stats.worst_ms() == pytest.approx(100.0)


def test_invalid_frames_are_ignored() -> None:
    stats = FrameStats()
    stats.add(0.0)
    stats.add(-1.0)
    stats.add(2.0)  # pausa o carga inicial

    assert stats.samples == 0
    assert stats.fps() == 0.0
    assert stats.mean_ms() == 0.0
    assert stats.worst_ms() == 0.0


def test_reset_clears_the_window() -> None:
    stats = FrameStats()
    stats.add(0.016)
    stats.reset()

    assert stats.samples == 0
    assert stats.fps() == 0.0


def test_window_must_be_positive() -> None:
    with pytest.raises(ValueError):
        FrameStats(window_seconds=0.0)
