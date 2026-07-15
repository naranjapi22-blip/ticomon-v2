import asyncio
import uuid

import pytest
import pytest_asyncio

from infrastructure.db_config import get_pool
from infrastructure.persistence.repositories.neon_creature_repository import (
    NeonCreatureRepository,
)
from infrastructure.species.neon_species_repository import NeonSpeciesRepository
from test.builders.creature_builder import CreatureBuilder


@pytest_asyncio.fixture
async def creature_repository_data():
    trainer_ids = [uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF for _ in range(3)]
    species_repository = NeonSpeciesRepository()
    species = await species_repository.get(1)
    yield trainer_ids, species

    pool = await get_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            "DELETE FROM creatures WHERE trainer_id = ANY($1::bigint[])",
            trainer_ids,
        )


@pytest.mark.asyncio
async def test_concurrent_repository_saves_get_distinct_collection_numbers(
    creature_repository_data,
):
    trainer_ids, species = creature_repository_data
    trainer_id = trainer_ids[0]
    repository = NeonCreatureRepository(NeonSpeciesRepository())

    async def save_one():
        return await repository.save(
            CreatureBuilder().with_species(species).with_trainer_id(trainer_id).build()
        )

    first, second = await asyncio.gather(save_one(), save_one())

    assert {first.collection_number, second.collection_number} == {1, 2}
    assert first.id != second.id

    async def save_for_trainer(trainer_id):
        return await repository.save(
            CreatureBuilder().with_species(species).with_trainer_id(trainer_id).build()
        )

    first, second = await asyncio.gather(
        save_for_trainer(trainer_ids[1]),
        save_for_trainer(trainer_ids[2]),
    )

    assert first.collection_number == 1
    assert second.collection_number == 1
