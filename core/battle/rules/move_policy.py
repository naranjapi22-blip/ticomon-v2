from dataclasses import dataclass
from typing import Any

from core.battle.rules.excluded_moves import EXCLUDED_MOVES, PENALIZED_MOVES


@dataclass(frozen=True)
class MoveData:
    move_id: str
    display_name: str
    category: str
    move_type: str
    base_power: int
    accuracy: int
    flags: frozenset[str] = frozenset()


def is_valid_ai_move(move_id: str, move_data: MoveData | None) -> bool:
    if move_data is None:
        return False

    if move_id in EXCLUDED_MOVES:
        return False

    if move_data.category.lower() == "status":
        return False

    if move_data.base_power <= 0:
        return False

    if move_data.accuracy < 80:
        return False

    blocked_flags = {"charge", "recharge", "mustcharge"}
    if blocked_flags & move_data.flags:
        return False

    return True


def pick_automatic_move(
    species_showdown_id: str,
    *,
    attack: int,
    special_attack: int,
    types: tuple[str, ...],
    learnset: dict[str, MoveData],
) -> tuple[str, str]:
    prefer_physical = attack >= special_attack
    best_score = float("-inf")
    best_move: tuple[str, str] | None = None

    for move_id, move_data in learnset.items():
        if not is_valid_ai_move(move_id, move_data):
            continue

        score = move_data.base_power

        if move_data.move_type in types:
            score += 40

        if prefer_physical and move_data.category.lower() == "physical":
            score += 15
        elif not prefer_physical and move_data.category.lower() == "special":
            score += 15

        accuracy = min(move_data.accuracy, 100)
        score += accuracy // 10
        score -= PENALIZED_MOVES.get(move_id, 0)

        if score > best_score:
            best_score = score
            best_move = (move_id, move_data.display_name)

    if best_move is None:
        return "tackle", "Tackle"

    return best_move


def _normalize_accuracy(raw_accuracy: Any) -> int:
    if raw_accuracy is True or raw_accuracy is None:
        return 100

    accuracy = float(raw_accuracy)
    if accuracy <= 1.0:
        return int(round(accuracy * 100))
    return int(accuracy)


def move_data_from_poke_env(move_id: str, raw: Any) -> MoveData:
    category = getattr(raw, "category", None)
    category_name = category.name if category is not None else "Status"
    move_type = getattr(getattr(raw, "type", None), "name", "normal")
    base_power = int(getattr(raw, "base_power", 0) or 0)
    accuracy = _normalize_accuracy(getattr(raw, "accuracy", 100))

    flags = frozenset(
        flag.name.lower() for flag in getattr(raw, "flags", []) if hasattr(flag, "name")
    )

    display_name = getattr(raw, "name", move_id.replace("-", " ").title())

    return MoveData(
        move_id=move_id,
        display_name=str(display_name),
        category=category_name.title(),
        move_type=str(move_type).lower(),
        base_power=base_power,
        accuracy=accuracy,
        flags=flags,
    )
