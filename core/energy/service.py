from datetime import UTC, datetime, timedelta

from core.energy.exceptions import NotEnoughEnergyException
from core.energy.repository import EnergyRepository
from core.energy.trainer_energy import TrainerEnergy


class EnergyService:

    def __init__(self, repository: EnergyRepository):
        self._repository = repository

    async def consume(self, trainer_id: int) -> None:

        energy = await self._repository.get(trainer_id)

        if energy is None:
            raise ValueError(f"Trainer {trainer_id} has no energy.")

        self.regenerate(energy)

        if energy.current_energy <= 0:
            raise NotEnoughEnergyException()

        energy.current_energy -= 1

        await self._repository.update(energy)

    def regenerate(self, energy: TrainerEnergy) -> None:

        now = datetime.now(UTC)

        hours = int((now - energy.last_regenerated_at) / timedelta(hours=1))

        if hours <= 0:
            return

        energy.current_energy = min(
            energy.max_energy,
            energy.current_energy + hours,
        )

        energy.last_regenerated_at += timedelta(hours=hours)

    async def get(
        self,
        trainer_id: int,
    ) -> TrainerEnergy:

        energy = await self._repository.get(
            trainer_id,
        )

        if energy is None:
            raise ValueError(f"Trainer {trainer_id} has no energy.")

        self.regenerate(
            energy,
        )

        await self._repository.update(
            energy,
        )

        return energy
