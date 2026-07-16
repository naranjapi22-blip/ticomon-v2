import pytest

from core.collection.catalog import COLLECTIONS
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


@pytest.mark.asyncio
async def test_find_many_by_names_loads_the_collection_catalog():
    names = tuple(
        dict.fromkeys(
            entry.species_name
            for definition in COLLECTIONS
            for entry in definition.entries
        )
    )

    species_by_name = await NeonSpeciesRepository().find_many_by_names(names)

    assert set(species_by_name) == set(names)
    assert {variant.name for variant in species_by_name["rotom"].variants} >= {
        "heat",
        "wash",
        "mow",
    }
