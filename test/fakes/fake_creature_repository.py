from core.creature.creature import Creature
from core.creature.creature_repository import CreatureRepository


class FakeCreatureRepository(CreatureRepository):
    """
    In-memory creature repository for tests.
    """

    def __init__(
        self,
        *creatures: Creature,
    ) -> None:
        self._creatures = {creature.id: creature for creature in creatures}

        self.saved: list[Creature] = []

    async def get(
        self,
        creature_id: int,
    ) -> Creature:
        return self._creatures[creature_id]

    async def save(
        self,
        creature: Creature,
    ) -> Creature:
        self._creatures[creature.id] = creature
        self.saved.append(creature)

        return creature

    async def has_species(
        self,
        trainer_id: int,
        species_id: int,
    ) -> bool:
        return any(
            creature.trainer_id == trainer_id and creature.species.id == species_id
            for creature in self._creatures.values()
        )

    async def count_creatures(
        self,
        trainer_id: int,
    ) -> int:
        return len(
            [
                creature
                for creature in self._creatures.values()
                if creature.trainer_id == trainer_id
            ]
        )

    async def count_species(
        self,
        trainer_id: int,
    ) -> int:
        return len(
            {
                creature.species.id
                for creature in self._creatures.values()
                if creature.trainer_id == trainer_id
            }
        )

    async def count_shinies(
        self,
        trainer_id: int,
    ) -> int:
        return len(
            [
                creature
                for creature in self._creatures.values()
                if creature.trainer_id == trainer_id and creature.is_shiny
            ]
        )

    async def get_by_collection_number(
        self,
        trainer_id: int,
        collection_number: int,
    ) -> Creature:
        return self._creatures[collection_number]

    async def get_by_species(
        self,
        trainer_id: int,
        species_id: int,
    ) -> list[Creature]:
        return [
            creature
            for creature in self._creatures.values()
            if creature.trainer_id == trainer_id and creature.species.id == species_id
        ]

    async def get_discovered_species(
        self,
        trainer_id: int,
    ) -> set[int]:
        return {
            creature.species.id
            for creature in self._creatures.values()
            if creature.trainer_id == trainer_id
        }
