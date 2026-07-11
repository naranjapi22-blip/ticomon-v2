from dataclasses import dataclass

from core.creature.creature import Creature
from core.trainer.trainer import Trainer


@dataclass(slots=True)
class StartAdventureResult:
    trainer: Trainer
    starter: Creature
