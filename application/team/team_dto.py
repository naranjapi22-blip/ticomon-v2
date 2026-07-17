from dataclasses import dataclass

from core.creature.creature import Creature


@dataclass(frozen=True, slots=True)
class TeamSlotDTO:
    slot: int
    creature: Creature


@dataclass(frozen=True, slots=True)
class TeamDTO:
    trainer_id: int
    slots: tuple[TeamSlotDTO, ...]
