from core.energy.repository import EnergyRepository
from core.energy.trainer_energy import TrainerEnergy


class FakeEnergyRepository(EnergyRepository):

    def __init__(self):
        self._energy: dict[int, TrainerEnergy] = {}

    async def get(
        self,
        trainer_id: int,
    ) -> TrainerEnergy | None:

        return self._energy.get(
            trainer_id,
        )

    async def save(
        self,
        energy: TrainerEnergy,
    ) -> None:

        self._energy[energy.trainer_id] = energy

    async def update(
        self,
        energy: TrainerEnergy,
    ) -> None:

        self._energy[energy.trainer_id] = energy
