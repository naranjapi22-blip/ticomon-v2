from __future__ import annotations

from core.creature.creature import Creature
from core.creature.creature_repository import CreatureRepository
from core.species.species_repository import SpeciesRepository


class CreatureCollectionService:
    def __init__(
        self,
        creature_repository: CreatureRepository,
        species_repository: SpeciesRepository,
    ) -> None:
        self._creature_repository = creature_repository
        self._species_repository = species_repository

    async def get_top_collection(
        self,
        trainer_id: int,
        pokemon_type: str | None = None,
    ) -> list[Creature]:
        creatures = await self._creature_repository.get_by_trainer(trainer_id)

        creatures = await self._apply_type_filter(
            creatures,
            pokemon_type,
        )

        return sorted(
            creatures,
            key=lambda creature: (
                -creature.iv_percentage,
                (
                    -creature.collection_number
                    if creature.collection_number is not None
                    else 0
                ),
                -creature.id if creature.id is not None else 0,
            ),
        )

    async def get_recent_collection(
        self,
        trainer_id: int,
        pokemon_type: str | None = None,
        shiny_only: bool = False,
    ) -> list[Creature]:
        creatures = await self._creature_repository.get_by_trainer(trainer_id)

        if shiny_only:
            creatures = [creature for creature in creatures if creature.is_shiny]

        creatures = await self._apply_type_filter(
            creatures,
            pokemon_type,
        )

        return sorted(
            creatures,
            key=lambda creature: (
                -(
                    creature.collection_number
                    if creature.collection_number is not None
                    else 0
                ),
                creature.id if creature.id is not None else 0,
            ),
        )

    async def _apply_type_filter(
        self,
        creatures: list[Creature],
        pokemon_type: str | None,
    ) -> list[Creature]:
        if pokemon_type is None:
            return creatures

        normalized_type = pokemon_type.strip().lower()
        valid_types = await self._known_types()

        if normalized_type not in valid_types:
            raise ValueError(f"Unknown Pokémon type: {pokemon_type}")

        return [
            creature
            for creature in creatures
            if normalized_type
            in (species_type.lower() for species_type in creature.species.types)
        ]

    async def _known_types(self) -> set[str]:
        species = await self._species_repository.get_all()

        return {pokemon_type.lower() for item in species for pokemon_type in item.types}
