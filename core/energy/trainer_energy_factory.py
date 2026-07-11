from datetime import UTC, datetime

from core.energy.trainer_energy import TrainerEnergy


class TrainerEnergyFactory:

    @staticmethod
    def create(trainer_id: int) -> TrainerEnergy:

        now = datetime.now(UTC)

        return TrainerEnergy(
            trainer_id=trainer_id,
            current_energy=12,
            max_energy=12,
            last_regenerated_at=now,
        )
