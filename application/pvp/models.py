from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PvpActionKind(str, Enum):
    MOVE = "move"
    SWITCH = "switch"
    FORFEIT = "forfeit"


@dataclass(frozen=True)
class PvpAction:
    kind: PvpActionKind
    identifier: str
    label: str
    detail: str = ""
    automatic: bool = False


@dataclass(frozen=True)
class PvpLegalActions:
    moves: tuple[PvpAction, ...] = ()
    switches: tuple[PvpAction, ...] = ()
    forced_switch: bool = False

    @property
    def all_actions(self) -> tuple[PvpAction, ...]:
        return self.switches if self.forced_switch else self.moves + self.switches


@dataclass(frozen=True)
class PvpBoardPlayer:
    trainer_id: int
    display_name: str
    active_name: str
    hp_percent: float
    status: str | None
    remaining: int
    ready: bool = False


@dataclass(frozen=True)
class PvpBoardState:
    challenger: PvpBoardPlayer
    opponent: PvpBoardPlayer
    turn: int
    event: str = ""
    finished: bool = False
    winner_id: int | None = None
    tie: bool = False


@dataclass(frozen=True)
class PvpPresentationStep:
    message: str
    board_state: PvpBoardState | None = None
    delay_seconds: float = 0.0


@dataclass
class PvpSessionRuntime:
    board: PvpBoardState | None = None
    pending_steps: list[PvpPresentationStep] = field(default_factory=list)
