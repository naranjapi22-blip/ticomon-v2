from abc import ABC, abstractmethod

from core.team.team_slot import TeamSlot


class TeamRepository(ABC):
    """
    Defines how trainer team slots are persisted.
    """

    @abstractmethod
    async def get_by_trainer(
        self,
        trainer_id: int,
    ) -> list[TeamSlot]:
        """
        Returns every slot assigned to the trainer, ordered by slot index.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_creature_id(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> TeamSlot | None:
        """
        Returns the team slot occupied by the given creature, if any.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_by_trainer(
        self,
        trainer_id: int,
    ) -> int:
        """
        Returns how many creatures are currently assigned to the team.
        """
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        trainer_id: int,
        slot: int,
        creature_id: int,
    ) -> TeamSlot:
        """
        Assigns a creature to an empty team slot.
        """
        raise NotImplementedError

    @abstractmethod
    async def replace_creature(
        self,
        trainer_id: int,
        old_creature_id: int,
        new_creature_id: int,
    ) -> TeamSlot:
        """
        Replaces one team creature with another in the same slot.
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_by_creature_id(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> None:
        """
        Removes a creature from the trainer team.
        """
        raise NotImplementedError
