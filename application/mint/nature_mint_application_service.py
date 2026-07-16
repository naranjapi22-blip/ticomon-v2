from dataclasses import dataclass

from core.creature.creature import Creature
from core.creature.nature import Nature
from core.creature.stat import Stat


@dataclass(frozen=True, slots=True)
class NatureMintPreview:
    creature: Creature
    mint_amount: int


@dataclass(frozen=True, slots=True)
class NatureMintResult:
    creature: Creature
    remaining_mints: int


class NatureMintApplicationService:
    def __init__(self, creature_repository, mint_repository) -> None:
        self._creature_repository = creature_repository
        self._mint_repository = mint_repository

    async def preview(
        self,
        trainer_id: int,
        collection_number: int,
    ) -> NatureMintPreview:
        creature = await self._creature_repository.get_by_collection_number(
            trainer_id,
            collection_number,
        )
        inventory = await self._mint_repository.get(trainer_id)
        if not inventory.has_one():
            raise ValueError("You do not have any Nature Mints.")
        return NatureMintPreview(creature, inventory.amount)

    async def apply(
        self,
        trainer_id: int,
        collection_number: int,
        increased: Stat | None,
        decreased: Stat | None,
    ) -> NatureMintResult:
        if increased is None and decreased is None:
            minted_nature = None
        elif increased is None or decreased is None:
            raise ValueError("Both increased and decreased stats are required.")
        else:
            minted_nature = Nature.from_effect(increased, decreased)

        creature, remaining_mints = await self._mint_repository.apply(
            trainer_id,
            collection_number,
            minted_nature,
        )
        return NatureMintResult(creature, remaining_mints)
