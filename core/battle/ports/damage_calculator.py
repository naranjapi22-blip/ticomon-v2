from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.battle.engine.battle_fighter import BattleFighter
from core.battle.engine.battle_team_state import RandomSource
from core.battle.rules.move_policy import MoveData


@dataclass(frozen=True)
class DamageResult:
    damage: int
    hit: bool
    critical: bool
    effectiveness_label: str
    message: str


class DamageCalculator(ABC):
    @abstractmethod
    def calculate(
        self,
        attacker: BattleFighter,
        defender: BattleFighter,
        *,
        random_source: RandomSource,
    ) -> DamageResult:
        raise NotImplementedError


class LearnsetProvider(ABC):
    @abstractmethod
    def get_learnset(self, species_showdown_id: str) -> dict[str, MoveData]:
        raise NotImplementedError
