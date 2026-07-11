from datetime import UTC, datetime

from core.trainer.trainer import Trainer


class TrainerFactory:

    @staticmethod
    def create(
        trainer_id: int,
        starter_creature_id: int,
    ) -> Trainer:

        started_at = datetime.now(UTC)

        return Trainer(
            trainer_id=trainer_id,
            starter_creature_id=starter_creature_id,
            started_at=started_at,
        )
