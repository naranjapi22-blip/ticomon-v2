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


@dataclass(frozen=True)
class SpeciesLearnsetQuery:
    species_id: int
    pokeapi_id: int
    species_name: str


@dataclass(frozen=True)
class SpeciesLearnset:
    species_showdown_id: str
    moves: dict[str, MoveData]


class LearnsetProvider(ABC):
    @abstractmethod
    def get_learnset(self, query: SpeciesLearnsetQuery) -> SpeciesLearnset:
        raise NotImplementedError
