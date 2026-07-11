from core.trainer.repository import TrainerRepository
from core.trainer.trainer import Trainer


class FakeTrainerRepository(TrainerRepository):

    def __init__(self):
        self._trainers = {}

    async def get(
        self,
        trainer_id: int,
    ) -> Trainer | None:
        return self._trainers.get(
            trainer_id,
        )

    async def exists(
        self,
        trainer_id: int,
    ) -> bool:
        return trainer_id in self._trainers

    async def save(
        self,
        trainer: Trainer,
    ) -> None:
        self._trainers[trainer.trainer_id] = trainer
