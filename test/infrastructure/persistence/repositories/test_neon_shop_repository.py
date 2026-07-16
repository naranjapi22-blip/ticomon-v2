import uuid
from types import SimpleNamespace

import pytest
from asyncpg.exceptions import UndefinedTableError

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from infrastructure.db_config import close_pool, get_pool
from infrastructure.persistence.repositories.neon_shop_repository import (
    NeonShopRepository,
)
from infrastructure.species.neon_species_repository import NeonSpeciesRepository
from scripts.create_collection_schema import create_collection_schema
from scripts.create_shop_schema import create_shop_schema
from test.builders.creature_builder import CreatureBuilder


@pytest.mark.asyncio
async def test_missing_shop_schema_has_explicit_error_and_single_traceback(
    monkeypatch, caplog
):
    repository = NeonShopRepository.__new__(NeonShopRepository)
    error = UndefinedTableError('relation "shop_purchase_receipts" does not exist')

    async def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(repository, "_purchase", fail)
    creature = SimpleNamespace(
        species=SimpleNamespace(name="alcremie", id=869),
        current_form=SimpleNamespace(id=80, name="salted-cream-love"),
    )

    with pytest.raises(ValueError, match="Shop schema is not initialized"):
        await repository.purchase(
            7, creature, SimpleNamespace(items=lambda: ()), "alcremie:80", "key"
        )
    records = [
        record for record in caplog.records if "shop_purchase_failed" in record.message
    ]
    assert len(records) == 1
    assert records[0].exc_info is not None


@pytest.mark.asyncio
@pytest.mark.neon_db
async def test_shop_purchase_records_the_canonical_collection_entry():
    await close_pool()
    await create_shop_schema()
    await create_collection_schema()
    pool = await get_pool()
    trainer_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
    created_ids = []
    receipt_key = f"collection-shop-test:{uuid.uuid4()}"
    try:
        async with pool.acquire() as connection:
            starter_id = await connection.fetchval(
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
            created_ids.append(starter_id)
            await connection.execute(
                """
                INSERT INTO trainers (trainer_id, starter_creature_id, started_at)
                VALUES ($1, $2, NOW())
                """,
                trainer_id,
                starter_id,
            )
            await connection.execute(
                """
                INSERT INTO trainer_candies (trainer_id, candy_type, amount)
                VALUES ($1, 'grass', 10)
                """,
                trainer_id,
            )

        species_repository = NeonSpeciesRepository()
        species = await species_repository.get(1)
        creature = (
            CreatureBuilder().with_species(species).with_trainer_id(trainer_id).build()
        )
        repository = NeonShopRepository(species_repository)
        stored, remaining, created = await repository.purchase(
            trainer_id,
            creature,
            CandyBundle.from_amounts(CandyAmount(CandyType.GRASS, 2)),
            "collection-test",
            receipt_key,
        )
        created_ids.append(stored.id)

        assert created is True
        assert remaining.get_amount(CandyType.GRASS) == 8
        async with pool.acquire() as connection:
            entry = await connection.fetchrow(
                """
                SELECT species_id, variant_id, source
                FROM trainer_collection_entries
                WHERE trainer_id = $1 AND species_id = $2 AND variant_id IS NULL
                """,
                trainer_id,
                species.id,
            )
        assert dict(entry) == {
            "species_id": species.id,
            "variant_id": None,
            "source": "shop",
        }
    finally:
        async with pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM shop_purchase_receipts WHERE trainer_id = $1", trainer_id
            )
            await connection.execute(
                "DELETE FROM trainer_collection_claims WHERE trainer_id = $1",
                trainer_id,
            )
            await connection.execute(
                "DELETE FROM trainer_collection_entries WHERE trainer_id = $1",
                trainer_id,
            )
            await connection.execute(
                "DELETE FROM trainer_candies WHERE trainer_id = $1", trainer_id
            )
            await connection.execute(
                "DELETE FROM trainers WHERE trainer_id = $1",
                trainer_id,
            )
            if created_ids:
                await connection.execute(
                    "DELETE FROM creatures WHERE id = ANY($1::bigint[])", created_ids
                )
        await close_pool()
