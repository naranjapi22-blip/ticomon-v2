from abc import ABC, abstractmethod


class ProfileRepository(ABC):
    """
    Defines how trainer profile information is persisted.
    """

    @abstractmethod
    async def get_featured_creature_id(
        self,
        trainer_id: int,
    ) -> int | None:
        raise NotImplementedError

    @abstractmethod
    async def set_featured_creature(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_selected_trainer(
        self,
        trainer_id: int,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def set_selected_trainer(
        self,
        trainer_id: int,
        selected_trainer: int,
    ) -> None:
        raise NotImplementedError
