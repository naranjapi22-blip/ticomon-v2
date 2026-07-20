from __future__ import annotations

from dataclasses import dataclass

from core.creature.ability import Ability
from core.creature.creature import Creature
from core.creature.move import CreatureMove, validate_equipped_moves


@dataclass(frozen=True)
class CreatureLoadout:
    creature: Creature
    ability: Ability | None
    moves: tuple[CreatureMove, ...]
    legal_moves: tuple[CreatureMove, ...] = ()


class CreatureLoadoutService:
    """Owns the read and update use cases for a persistent PvP loadout."""

    def __init__(self, creature_repository, catalog) -> None:
        self._creature_repository = creature_repository
        self._catalog = catalog

    async def get_loadout(self, trainer_id: int, collection_number: int):
        creature = await self._creature_repository.get_by_collection_number(
            trainer_id, collection_number
        )
        legal_moves = await self._legal_moves(creature)
        abilities = self._catalog.abilities_for(creature.species)
        ability = next(
            (item for item in abilities if item.id == creature.ability_id), None
        )
        move_by_id = {item.id: item for item in legal_moves}
        equipped = tuple(
            move_by_id[move_id] for move_id in creature.moves if move_id in move_by_id
        )
        return CreatureLoadout(creature, ability, equipped, legal_moves)

    async def update_moves(
        self,
        trainer_id: int,
        collection_number: int,
        moves: tuple[str, ...] | list[str],
    ) -> CreatureLoadout:
        creature = await self._creature_repository.get_by_collection_number(
            trainer_id, collection_number
        )
        legal_moves = await self._legal_moves(creature)
        normalized = validate_equipped_moves(moves, {item.id for item in legal_moves})
        updated = await self._creature_repository.update_moves(
            trainer_id=trainer_id,
            collection_number=collection_number,
            moves=normalized,
            ability_id=creature.ability_id,
        )
        return await self.get_loadout(updated.trainer_id, updated.collection_number)

    async def _legal_moves(self, creature: Creature) -> tuple[CreatureMove, ...]:
        get_legal_moves = getattr(self._creature_repository, "get_legal_moves", None)
        if get_legal_moves is not None:
            persisted = tuple(await get_legal_moves(creature.species.id))
            if not persisted:
                return self._catalog.moves_for(creature.species)
            catalog_by_id = {
                item.id: item for item in self._catalog.moves_for(creature.species)
            }
            return tuple(catalog_by_id.get(item.id, item) for item in persisted)
        return self._catalog.moves_for(creature.species)
