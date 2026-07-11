from core.trainer.trainer import Trainer


class TrainerMapper:

    @staticmethod
    def from_row(row) -> Trainer:
        return Trainer(
            trainer_id=row["trainer_id"],
            starter_creature_id=row["starter_creature_id"],
            started_at=row["started_at"],
        )
