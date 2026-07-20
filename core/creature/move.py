from __future__ import annotations

from dataclasses import dataclass

MAX_CREATURE_MOVES = 4


def canonicalize_move_id(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("'", "")


@dataclass(frozen=True)
class CreatureMove:
    id: str
    display_name: str
    move_type: str
    category: str
    base_power: int | None
    accuracy: int | None
    pp: int
    priority: int = 0


def validate_moves(moves: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized = tuple(canonicalize_move_id(move) for move in moves)
    if len(normalized) > MAX_CREATURE_MOVES:
        raise ValueError("A creature can equip at most four moves.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("A creature cannot equip duplicate moves.")
    return normalized
