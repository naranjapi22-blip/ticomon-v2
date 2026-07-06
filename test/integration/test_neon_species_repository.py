import pytest

from infrastructure.species.neon_species_repository import (
    NeonSpeciesRepository,
)


@pytest.mark.asyncio
async def test_get_species_by_id():

    repository = NeonSpeciesRepository()

    species = await repository.get(25)

    assert species.id == 25
    assert species.name == "pikachu"


@pytest.mark.asyncio
async def test_find_species_by_name():

    repository = NeonSpeciesRepository()

    species = await repository.find_by_name("pikachu")

    assert species is not None
    assert species.id == 25


@pytest.mark.asyncio
async def test_get_all_species():

    repository = NeonSpeciesRepository()

    species = await repository.get_all()

    assert len(species) >= 1025
