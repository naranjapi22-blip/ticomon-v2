from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TrainerEnergy:
    trainer_id: int
    current_energy: int
    max_energy: int
    last_regenerated_at: datetime
