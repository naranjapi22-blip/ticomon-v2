from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BattleStepType(str, Enum):
    START = "start"
    MOVE = "move"
    DAMAGE = "damage"
    ATTACK = "attack"
    SWITCH = "switch"
    VICTORY = "victory"


@dataclass(frozen=True)
class BattleStep:
    step_type: BattleStepType
    side_a_name: str
    side_b_name: str
    message: str
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    pause_seconds: float = 1.5
