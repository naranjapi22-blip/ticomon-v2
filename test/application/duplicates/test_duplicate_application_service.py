import pytest

from application.duplicates.duplicate_application_service import (
    DuplicateApplicationService,
)
from test.builders.species_builder import SpeciesBuilder


class _CreatureRepository:
    async def get_duplicate_species(self, trainer_id):
        return [(1, 3), (2, 2)]


class _SpeciesRepository:
    def __init__(self, *species):
        self.species = {item.id: item for item in species}
        self.get_calls = []
        self.get_many_calls = []

    async def get(self, species_id):
        self.get_calls.append(species_id)
        return self.species[species_id]

    async def get_many(self, species_ids):
        self.get_many_calls.append(list(species_ids))
        return [self.species[item] for item in dict.fromkeys(species_ids)]


@pytest.mark.asyncio
async def test_get_duplicates_loads_species_once_in_a_batch():
    species_repository = _SpeciesRepository(
        SpeciesBuilder().with_id(1).with_name("One").build(),
        SpeciesBuilder().with_id(2).with_name("Two").build(),
    )
    service = DuplicateApplicationService(
        _CreatureRepository(),
        species_repository,
    )

    result = await service.get_duplicates(1)

    assert [(item.species_id, item.species_name) for item in result] == [
        (1, "One"),
        (2, "Two"),
    ]
    assert species_repository.get_calls == []
    assert species_repository.get_many_calls == [[1, 2]]


@pytest.mark.asyncio
async def test_get_duplicates_by_type_does_not_reload_species():
    species_repository = _SpeciesRepository(
        SpeciesBuilder().with_id(1).with_types(["Fire"]).build(),
        SpeciesBuilder().with_id(2).with_types(["water"]).build(),
    )
    service = DuplicateApplicationService(
        _CreatureRepository(),
        species_repository,
    )

    result = await service.get_duplicates_by_type(1, "fire")

    assert [item.species_id for item in result] == [1]
    assert species_repository.get_calls == []
    assert species_repository.get_many_calls == [[1, 2]]
