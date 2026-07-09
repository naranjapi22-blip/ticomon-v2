from dataclasses import dataclass

from application.trainer.trainer import Trainer
from core.creature.creature import Creature


@dataclass(frozen=True)
class TrainerProfileDTO:
    trainer_id: int

    trainer: Trainer

    total_captured: int
    unique_species: int
    shiny_count: int

    completion_percentage: float

    featured_creature: Creature | None
