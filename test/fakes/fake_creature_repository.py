from dataclasses import replace

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

        self._collection_numbers = {}

        for index, creature in enumerate(creatures, start=1):
            self._collection_numbers[index] = creature

            if creature.collection_number is not None:
                self._collection_numbers[creature.collection_number] = creature

        self.saved: list[Creature] = []
        self.updated: list[Creature] = []
        self.deleted: list[Creature] = []
        self.legal_moves = {}

    async def get(
        self,
        creature_id: int,
    ) -> Creature:
        return self._creatures[creature_id]

    async def get_many(
        self,
        creature_ids: list[int] | tuple[int, ...],
    ) -> list[Creature]:
        return [
            self._creatures[creature_id]
            for creature_id in creature_ids
            if creature_id in self._creatures
        ]

    async def save(
        self,
        creature: Creature,
    ) -> Creature:
        self._creatures[creature.id] = creature

        if creature.collection_number is None:
            next_collection_number = max(self._collection_numbers, default=0) + 1
            self._collection_numbers[next_collection_number] = creature

        if creature.collection_number is not None:
            self._collection_numbers[creature.collection_number] = creature

        self.saved.append(creature)

        return creature

    async def update(
        self,
        creature: Creature,
    ) -> Creature:
        self._creatures[creature.id] = creature

        if creature.collection_number is not None:
            self._collection_numbers[creature.collection_number] = creature

        self.updated.append(creature)

        return creature

    async def get_legal_moves(self, species_id: int):
        return tuple(self.legal_moves.get(species_id, ()))

    async def update_moves(self, *, trainer_id, collection_number, moves, ability_id):
        creature = await self.get_by_collection_number(trainer_id, collection_number)
        if creature.ability_id != ability_id:
            raise ValueError("The creature loadout could not be updated.")
        updated = replace(creature, moves=tuple(moves))
        return await self.update(updated)

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
        creature = self._collection_numbers[collection_number]

        if creature.trainer_id != trainer_id:
            raise ValueError(f"Creature #{collection_number} was not found.")

        return creature

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

    async def get_by_trainer(
        self,
        trainer_id: int,
    ) -> list[Creature]:
        return sorted(
            [
                creature
                for creature in self._creatures.values()
                if creature.trainer_id == trainer_id
            ],
            key=lambda creature: (
                (
                    creature.collection_number
                    if creature.collection_number is not None
                    else 0
                ),
                creature.id if creature.id is not None else 0,
            ),
        )

    async def get_discovered_species(
        self,
        trainer_id: int,
    ) -> set[int]:
        return {
            creature.species.id
            for creature in self._creatures.values()
            if creature.trainer_id == trainer_id
        }

    async def delete(
        self,
        creature: Creature,
    ) -> None:
        self._creatures.pop(creature.id, None)

        if creature.collection_number is not None:
            self._collection_numbers.pop(
                creature.collection_number,
                None,
            )

        self.deleted.append(creature)

    async def get_duplicate_species(
        self,
        trainer_id: int,
    ) -> list[tuple[int, int]]:
        return []
