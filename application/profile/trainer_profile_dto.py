from dataclasses import dataclass

from core.creature.creature import Creature


@dataclass(frozen=True)
class TrainerProfileDTO:
    trainer_id: int

    total_captured: int
    unique_species: int
    shiny_count: int

    completion_percentage: float

    featured_creature: Creature | None
