from abc import ABC, abstractmethod

from core.trainer.trainer import Trainer


class TrainerRepository(ABC):

    @abstractmethod
    async def get(self, trainer_id: int) -> Trainer | None: ...

    @abstractmethod
    async def exists(self, trainer_id: int) -> bool: ...

    @abstractmethod
    async def save(self, trainer: Trainer) -> None: ...
