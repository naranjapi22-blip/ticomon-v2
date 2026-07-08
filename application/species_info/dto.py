from dataclasses import dataclass

from core.creature.creature import Creature
from core.species.species import Species


@dataclass(frozen=True)
class SpeciesInfoDTO:
    species: Species
    creatures: tuple[Creature, ...]
