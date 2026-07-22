from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BattlePresentationSide:
    """Visual data for one stable side of a battle."""

    trainer_id: int
    display_name: str
    active_name: str | None
    sprite_identifier: str | None
    shiny: bool
    hp_current: int
    hp_max: int
    hp_fraction: float
    status: str | None
    fainted: bool
    remaining: int
    capture_sprite_url: str | None = None


@dataclass(frozen=True)
class BattlePresentationState:
    """Engine-independent state consumed by the battle presentation layer."""

    top: BattlePresentationSide
    bottom: BattlePresentationSide
    turn: int
    last_event: str
    terminal: bool = False
    winner_id: int | None = None
    draw: bool = False
    waiting_text: str | None = None
    last_decisive_event: object | None = None
    last_decisive_event_turn: int | None = None
