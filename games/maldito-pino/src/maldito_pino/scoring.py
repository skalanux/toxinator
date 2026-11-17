"""Bowling rules and scoring for the first playable slice."""

from __future__ import annotations

from dataclasses import dataclass

FRAMES = 10
PINS = 10


@dataclass(frozen=True, slots=True)
class RollResult:
    pins: int
    frame: int
    ball: int
    strike: bool
    spare: bool
    frame_over: bool
    game_over: bool


class BowlingMatch:
    """Standard ten-pin scoring with a 10th-frame bonus.

    The game owns the pin identities; this class owns frames, balls, standing
    count and score. It accepts 0..standing pins per roll and clamps bad input.
    """

    def __init__(self) -> None:
        self.frames: list[list[int]] = [[] for _ in range(FRAMES)]
        self.frame = 0
        self.ball = 0
        self.standing = PINS
        self.game_over = False
        self.last: RollResult | None = None

    def roll(self, pins: int) -> RollResult:
        if self.game_over:
            raise RuntimeError("la partida terminó")
        if self.frame >= FRAMES:
            raise RuntimeError("no hay frame disponible")

        pins = max(0, min(int(pins), self.standing))
        frame_before = self.frame
        ball_before = self.ball
        self.frames[frame_before].append(pins)
        self.standing -= pins

        strike = ball_before == 0 and pins == PINS
        spare = ball_before > 0 and self.standing == 0 and not strike
        frame_over = False

        if frame_before < FRAMES - 1:
            if ball_before == 0 and pins == PINS or ball_before == 1:
                frame_over = True
                self._next_frame()
            else:
                self.ball = 1
        else:
            if ball_before == 0:
                if pins == PINS:
                    self.standing = PINS
                self.ball = 1
            elif ball_before == 1:
                first, second = self.frames[FRAMES - 1][:2]
                if first == PINS or first + second == PINS:
                    self.standing = PINS
                    self.ball = 2
                else:
                    self.game_over = True
                    frame_over = True
                    self.frame = FRAMES
                    self.ball = 0
                    self.standing = PINS
            else:
                self.game_over = True
                frame_over = True
                self.frame = FRAMES
                self.ball = 0
                self.standing = PINS

        self.last = RollResult(
            pins=pins,
            frame=frame_before,
            ball=ball_before,
            strike=strike,
            spare=spare,
            frame_over=frame_over,
            game_over=self.game_over,
        )
        return self.last

    def _next_frame(self) -> None:
        self.ball = 0
        self.standing = PINS
        self.frame += 1
        if self.frame >= FRAMES:
            self.game_over = True
            self.frame = FRAMES
            self.ball = 0

    def frame_scores(self) -> list[int | None]:
        flat = [roll for frame in self.frames for roll in frame]
        scores: list[int | None] = []
        index = 0
        cumulative = 0

        for _ in range(FRAMES - 1):
            if index + 1 >= len(flat):
                scores.append(None)
                continue
            first = flat[index]
            second = flat[index + 1]
            if first == PINS:
                if index + 2 >= len(flat):
                    scores.append(None)
                    index += 1
                    continue
                cumulative += PINS + flat[index + 1] + flat[index + 2]
                index += 1
            elif first + second == PINS:
                if index + 2 >= len(flat):
                    scores.append(None)
                    index += 2
                    continue
                cumulative += PINS + flat[index + 2]
                index += 2
            else:
                cumulative += first + second
                index += 2
            scores.append(cumulative)

        tenth = self.frames[FRAMES - 1]
        if len(tenth) < 2 or (tenth[0] == PINS or sum(tenth[:2]) == PINS) and len(tenth) < 3:
            scores.append(None)
        else:
            cumulative += sum(tenth)
            scores.append(cumulative)
        return scores

    @property
    def total(self) -> int:
        scores = [score for score in self.frame_scores() if score is not None]
        return scores[-1] if scores else 0

    def frame_marks(self) -> list[str]:
        marks: list[str] = []
        for frame in self.frames:
            if not frame:
                marks.append("")
                continue
            if frame[0] == PINS:
                marks.append("X")
            elif len(frame) >= 2 and sum(frame[:2]) == PINS:
                marks.append("/")
            else:
                marks.append("".join(_mark(roll) for roll in frame))
        return marks

    @property
    def current_frame(self) -> int:
        return min(self.frame + 1, FRAMES)

    @property
    def current_ball(self) -> int:
        return self.ball + 1


def _mark(pins: int) -> str:
    if pins == PINS:
        return "X"
    if pins == 0:
        return "-"
    return str(pins)
