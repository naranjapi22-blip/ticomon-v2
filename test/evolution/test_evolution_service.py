import pytest

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_service import EvolutionService
from core.species.species import Species
from core.species.species_repository import SpeciesRepository
from test.builders.creature_builder import CreatureBuilder
from test.builders.species_builder import SpeciesBuilder


class FakeSpeciesRepository(SpeciesRepository):

    def __init__(
        self,
        *species: Species,
    ) -> None:
        self._species = {s.id: s for s in species}

    async def get(
        self,
        species_id: int,
    ) -> Species:
        return self._species[species_id]

    async def find_by_name(
        self,
        name: str,
    ) -> Species | None:
        raise NotImplementedError

    async def get_all(
        self,
    ):
        raise NotImplementedError

    async def find_by_spawn_rarity(
        self,
        rarity,
    ):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_evolve_changes_species_and_consumes_candies():

    first = SpeciesBuilder().with_id(1).build()

    second = SpeciesBuilder().with_id(2).build()

    service = EvolutionService(
        policy=EvolutionPolicy(),
        species_repository=FakeSpeciesRepository(
            first,
            second,
        ),
    )

    creature = CreatureBuilder().with_species(first).build()

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                25,
            )
        )
    )

    result = await service.evolve(
        creature,
        inventory,
    )

    assert result.success
    assert creature.species.id == 2
    assert (
        inventory.get_amount(
            CandyType.FIRE,
        )
        == 0
    )


@pytest.mark.asyncio
async def test_evolve_does_not_change_species_when_validation_fails():

    first = SpeciesBuilder().with_id(1).build()

    second = SpeciesBuilder().with_id(2).build()

    service = EvolutionService(
        policy=EvolutionPolicy(),
        species_repository=FakeSpeciesRepository(
            first,
            second,
        ),
    )

    creature = CreatureBuilder().with_species(first).build()

    inventory = CandyInventory()

    result = await service.evolve(
        creature,
        inventory,
    )

    assert not result.success
    assert creature.species.id == 1


@pytest.mark.asyncio
async def test_evolve_returns_new_species():

    first = SpeciesBuilder().with_id(1).build()

    second = SpeciesBuilder().with_id(2).build()

    service = EvolutionService(
        policy=EvolutionPolicy(),
        species_repository=FakeSpeciesRepository(
            first,
            second,
        ),
    )

    creature = CreatureBuilder().with_species(first).build()

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                25,
            )
        )
    )

    result = await service.evolve(
        creature,
        inventory,
    )

    assert result.previous_species.id == 1
    assert result.evolved_species.id == 2
