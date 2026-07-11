from abc import ABC, abstractmethod

from core.creature.creature import Creature


class CreatureRepository(ABC):
    """
    Defines how Creature entities are persisted.
    """

    @abstractmethod
    async def save(
        self,
        creature: Creature,
    ) -> Creature:
        """
        Persists a Creature and returns the stored entity.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        creature_id: int,
    ) -> Creature:
        """
        Returns a Creature by its identifier.
        """
        raise NotImplementedError

    @abstractmethod
    async def has_species(
        self,
        trainer_id: int,
        species_id: int,
    ) -> bool:
        """
        Returns whether the trainer has already captured the species.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_creatures(
        self,
        trainer_id: int,
    ) -> int:
        """
        Returns the total number of creatures owned by the trainer.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_species(
        self,
        trainer_id: int,
    ) -> int:
        """
        Returns the number of unique species owned by the trainer.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_shinies(
        self,
        trainer_id: int,
    ) -> int:
        """
        Returns the number of shiny creatures owned by the trainer.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_collection_number(
        self,
        trainer_id: int,
        collection_number: int,
    ) -> Creature:
        """
        Returns a trainer's creature by its collection number.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_species(
        self,
        trainer_id: int,
        species_id: int,
    ) -> list[Creature]:
        """
        Returns all creatures of the given species owned by the trainer.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_duplicate_species(
        self,
        trainer_id: int,
    ) -> list[tuple[int, int]]:
        """
        Returns species ids with more than one owned creature.

        Returns:
            List of tuples:
            (species_id, amount)
        """
        raise NotImplementedError

    @abstractmethod
    async def get_discovered_species(
        self,
        trainer_id: int,
    ) -> set[int]:
        """
        Returns the ids of every species discovered by the trainer.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        creature: Creature,
    ) -> Creature:
        """
        Updates an existing Creature.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        creature: Creature,
    ) -> None:
        """
        Deletes an existing Creature.
        """
        raise NotImplementedError
