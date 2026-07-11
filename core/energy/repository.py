from abc import ABC, abstractmethod

from core.energy.trainer_energy import TrainerEnergy


class EnergyRepository(ABC):

    @abstractmethod
    async def get(self, trainer_id: int) -> TrainerEnergy | None: ...

    @abstractmethod
    async def save(self, energy: TrainerEnergy) -> None: ...

    @abstractmethod
    async def update(self, energy: TrainerEnergy) -> None: ...
