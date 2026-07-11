from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Trainer:
    trainer_id: int
    starter_creature_id: int
    started_at: datetime
