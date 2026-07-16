import asyncio
import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from core.collection.history import CollectionEntrySource
from infrastructure.db_config import close_pool, get_pool
from infrastructure.persistence.repositories.neon_collection_history_repository import (
    NeonCollectionHistoryRepository,
)
from scripts.create_collection_schema import create_collection_schema
from scripts.create_mint_schema import create_mint_schema


@pytest_asyncio.fixture
async def collection_trainer_factory():
    await close_pool()
    await create_mint_schema()
    await create_collection_schema()
    pool = await get_pool()
    trainer_ids = []
    creature_ids = []

    async def create():
        trainer_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
        async with pool.acquire() as connection:
            creature_id = await connection.fetchval(
                """
                INSERT INTO creatures (
                    trainer_id, original_trainer_id, collection_number,
                    species_id, current_form_id, is_shiny, nature, size,
                    hp_iv, attack_iv, defense_iv, special_attack_iv,
                    special_defense_iv, speed_iv
                )
                VALUES (
                    $1, $1, 1, 1, NULL, FALSE, 'hardy', 1.0,
                    31, 31, 31, 31, 31, 31
                )
                RETURNING id
                """,
                trainer_id,
            )
            await connection.execute(
                """
                INSERT INTO trainers (trainer_id, starter_creature_id, started_at)
                VALUES ($1, $2, NOW())
                """,
                trainer_id,
                creature_id,
            )
        trainer_ids.append(trainer_id)
        creature_ids.append(creature_id)
        return trainer_id, creature_id

    yield create

    async with pool.acquire() as connection:
        if trainer_ids:
            await connection.execute(
                "DELETE FROM trainer_collection_claims WHERE trainer_id = ANY($1)",
                trainer_ids,
            )
            await connection.execute(
                "DELETE FROM trainer_collection_entries WHERE trainer_id = ANY($1)",
                trainer_ids,
            )
            await connection.execute(
                "DELETE FROM trainer_candies WHERE trainer_id = ANY($1)",
                trainer_ids,
            )
            await connection.execute(
                "DELETE FROM trainer_mints WHERE trainer_id = ANY($1)",
                trainer_ids,
            )
            await connection.execute(
                "DELETE FROM trainers WHERE trainer_id = ANY($1)", trainer_ids
            )
        if creature_ids:
            await connection.execute(
                "DELETE FROM creatures WHERE id = ANY($1::bigint[])", creature_ids
            )
    await close_pool()


def _creature(trainer_id: int, creature_id: int):
    return SimpleNamespace(
        trainer_id=trainer_id,
        id=creature_id,
        species=SimpleNamespace(id=1, name="bulbasaur"),
        current_form=None,
    )


@pytest.mark.asyncio
async def test_entry_claim_is_atomic_and_idempotent(collection_trainer_factory):
    trainer_id, creature_id = await collection_trainer_factory()
    repository = NeonCollectionHistoryRepository()
    creature = _creature(trainer_id, creature_id)
    reward = CandyBundle.from_amounts(CandyAmount(CandyType.ROCK, 20))

    assert await repository.record_creature(creature, CollectionEntrySource.TRADE)
    assert not await repository.record_creature(creature, CollectionEntrySource.TRADE)
    results = await asyncio.gather(
        repository.claim(
            trainer_id,
            "fossil_restoration",
            1,
            ((1, None),),
            reward,
            1,
        ),
        repository.claim(
            trainer_id,
            "fossil_restoration",
            1,
            ((1, None),),
            reward,
            1,
        ),
    )

    assert sorted(results) == [False, True]
    pool = await get_pool()
    async with pool.acquire() as connection:
        candy_amount = await connection.fetchval(
            """
            SELECT amount FROM trainer_candies
            WHERE trainer_id = $1 AND candy_type = 'rock'
            """,
            trainer_id,
        )
        mint_amount = await connection.fetchval(
            "SELECT amount FROM trainer_mints WHERE trainer_id = $1",
            trainer_id,
        )
        claims = await connection.fetchval(
            "SELECT COUNT(*) FROM trainer_collection_claims WHERE trainer_id = $1",
            trainer_id,
        )
    assert candy_amount == 20
    assert mint_amount == 1
    assert claims == 1


@pytest.mark.asyncio
async def test_claim_requires_a_currently_owned_canonical_entry(
    collection_trainer_factory,
):
    trainer_id, creature_id = await collection_trainer_factory()
    repository = NeonCollectionHistoryRepository()
    await repository.record_creature(
        _creature(trainer_id, creature_id), CollectionEntrySource.TRADE
    )
    pool = await get_pool()
    async with pool.acquire() as connection:
        await connection.execute("DELETE FROM creatures WHERE id = $1", creature_id)

    with pytest.raises(ValueError, match="current collection"):
        await repository.claim(
            trainer_id,
            "fossil_restoration",
            1,
            ((1, None),),
            CandyBundle(),
            0,
        )

    history = await repository.entries_for_trainer(trainer_id)
    assert history[0].source is CollectionEntrySource.TRADE
    assert await repository.claimed_milestones(trainer_id) == frozenset()
