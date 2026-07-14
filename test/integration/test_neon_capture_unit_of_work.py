import asyncio
import uuid
from datetime import UTC, date, datetime

import pytest
import pytest_asyncio

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.safari import SafariMapInfluence
from infrastructure.db_config import get_pool
from infrastructure.persistence.repositories.neon_capture_unit_of_work import (
    NeonCaptureUnitOfWork,
)
from infrastructure.species.neon_species_repository import NeonSpeciesRepository
from scripts.create_safari_schema import create_safari_schema
from test.builders.creature_builder import CreatureBuilder

NOW = datetime(2026, 7, 13, 12, tzinfo=UTC)


@pytest_asyncio.fixture
async def capture_data():
    await create_safari_schema()
    trainer_ids = [uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF for _ in range(3)]
    guild_ids = [uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF for _ in range(3)]
    species = await NeonSpeciesRepository().get(1)
    yield trainer_ids, guild_ids, species

    pool = await get_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            "DELETE FROM safari_unlocks WHERE guild_id = ANY($1::bigint[])",
            guild_ids,
        )
        await connection.execute(
            (
                "DELETE FROM safari_daily_active_trainers "
                "WHERE guild_id = ANY($1::bigint[])"
            ),
            guild_ids,
        )
        await connection.execute(
            "DELETE FROM safari_daily_worlds WHERE guild_id = ANY($1::bigint[])",
            guild_ids,
        )
        await connection.execute(
            "DELETE FROM trainer_candies WHERE trainer_id = ANY($1::bigint[])",
            trainer_ids,
        )
        await connection.execute(
            "DELETE FROM creatures WHERE trainer_id = ANY($1::bigint[])",
            trainer_ids,
        )


@pytest.mark.asyncio
async def test_transaction_rolls_back_creature_candies_and_daily_world(
    capture_data,
):
    trainer_ids, guild_ids, species = capture_data
    trainer_id = trainer_ids[0]
    guild_id = guild_ids[0]
    unit_of_work = NeonCaptureUnitOfWork()

    with pytest.raises(RuntimeError, match="rollback"):
        async with unit_of_work.transaction() as transaction:
            saved_creature = await transaction.save_creature(
                _creature(trainer_id, species)
            )
            assert saved_creature.original_trainer_id == trainer_id
            inventory = CandyInventory()
            inventory.add(_candy_bundle())
            await transaction.save_candy_inventory(trainer_id, inventory)
            world = await transaction.get_or_create_daily_world(
                guild_id,
                NOW.date(),
            )
            world.daily_capture_count = 50
            await transaction.save_daily_world(world)
            await transaction.register_daily_active_trainer_if_absent(
                guild_id,
                NOW.date(),
                trainer_id,
                NOW,
            )
            raise RuntimeError("rollback")

    pool = await get_pool()
    async with pool.acquire() as connection:
        assert (
            await connection.fetchval(
                "SELECT COUNT(*) FROM creatures WHERE trainer_id = $1",
                trainer_id,
            )
            == 0
        )
        assert (
            await connection.fetchval(
                "SELECT COUNT(*) FROM creatures WHERE original_trainer_id = $1",
                trainer_id,
            )
            == 0
        )
        assert (
            await connection.fetchval(
                "SELECT COUNT(*) FROM trainer_candies WHERE trainer_id = $1",
                trainer_id,
            )
            == 0
        )
        assert (
            await connection.fetchval(
                "SELECT COUNT(*) FROM safari_daily_worlds WHERE guild_id = $1",
                guild_id,
            )
            == 0
        )
        assert (
            await connection.fetchval(
                "SELECT COUNT(*) FROM safari_daily_active_trainers WHERE guild_id = $1",
                guild_id,
            )
            == 0
        )


@pytest.mark.asyncio
async def test_concurrent_captures_get_distinct_collection_numbers(capture_data):
    trainer_ids, guild_ids, species = capture_data
    trainer_id = trainer_ids[0]

    async def save_one(guild_id):
        async with NeonCaptureUnitOfWork().transaction() as transaction:
            return await transaction.save_creature(_creature(trainer_id, species))

    first, second = await asyncio.gather(
        save_one(guild_ids[0]),
        save_one(guild_ids[1]),
    )

    assert {first.collection_number, second.collection_number} == {1, 2}


@pytest.mark.asyncio
async def test_different_trainers_allocate_collection_numbers_independently(
    capture_data,
):
    trainer_ids, guild_ids, species = capture_data

    async def save_one(trainer_id):
        async with NeonCaptureUnitOfWork().transaction() as transaction:
            return await transaction.save_creature(_creature(trainer_id, species))

    first, second = await asyncio.gather(
        save_one(trainer_ids[0]),
        save_one(trainer_ids[1]),
    )

    assert first.collection_number == 1
    assert second.collection_number == 1


@pytest.mark.asyncio
async def test_daily_world_lock_serializes_progress_updates(capture_data):
    _, guild_ids, _ = capture_data
    guild_id = guild_ids[0]

    async def increment_world():
        async with NeonCaptureUnitOfWork().transaction() as transaction:
            world = await transaction.get_or_create_daily_world(
                guild_id,
                date(2026, 7, 13),
            )
            world.daily_capture_count += 1
            world.current_influence = SafariMapInfluence(
                {"grass": world.current_influence.get("grass") + 1}
            )
            await transaction.save_daily_world(world)

    await asyncio.gather(increment_world(), increment_world())

    pool = await get_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            "SELECT * FROM safari_daily_worlds WHERE guild_id = $1",
            guild_id,
        )
    assert row["daily_capture_count"] == 2


def _creature(trainer_id, species):
    return CreatureBuilder().with_species(species).with_trainer_id(trainer_id).build()


def _candy_bundle():
    return CandyBundle.from_amounts(CandyAmount(CandyType.GRASS, 2))
