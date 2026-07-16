import json
import logging

from asyncpg.exceptions import UndefinedTableError

from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.collection.history import CollectionEntrySource, TrainerCollectionEntry
from core.collection.repository import CollectionHistoryRepository
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.candy_mapper import CandyMapper

logger = logging.getLogger(__name__)

_SCHEMA_ERROR = (
    "Collections schema is not initialized. Run scripts/create_collection_schema.py."
)


class NeonCollectionHistoryRepository(CollectionHistoryRepository):
    def __init__(self) -> None:
        self._candy_mapper = CandyMapper()

    async def record_creature(self, creature, source: CollectionEntrySource) -> bool:
        if creature.trainer_id is None or creature.id is None:
            raise ValueError(
                "Collection entries require a persisted creature and trainer."
            )
        try:
            pool = await get_pool()
            async with pool.acquire() as connection:
                row = await connection.fetchrow(
                    """
                    INSERT INTO trainer_collection_entries (
                        trainer_id, species_id, variant_id, source
                    )
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                    RETURNING trainer_id
                    """,
                    creature.trainer_id,
                    creature.species.id,
                    (
                        creature.current_form.id
                        if creature.current_form is not None
                        else None
                    ),
                    source.value,
                )
        except UndefinedTableError as error:
            raise ValueError(_SCHEMA_ERROR) from error
        return row is not None

    async def entries_for_trainer(
        self, trainer_id: int
    ) -> tuple[TrainerCollectionEntry, ...]:
        try:
            pool = await get_pool()
            async with pool.acquire() as connection:
                rows = await connection.fetch(
                    """
                    SELECT trainer_id, species_id, variant_id, first_obtained_at, source
                    FROM trainer_collection_entries
                    WHERE trainer_id = $1
                    ORDER BY first_obtained_at, species_id, variant_id NULLS FIRST
                    """,
                    trainer_id,
                )
        except UndefinedTableError as error:
            raise ValueError(_SCHEMA_ERROR) from error
        return tuple(
            TrainerCollectionEntry(
                trainer_id=row["trainer_id"],
                species_id=row["species_id"],
                variant_id=row["variant_id"],
                first_obtained_at=row["first_obtained_at"],
                source=CollectionEntrySource(row["source"]),
            )
            for row in rows
        )

    async def claimed_milestones(self, trainer_id: int) -> frozenset[tuple[str, int]]:
        try:
            pool = await get_pool()
            async with pool.acquire() as connection:
                rows = await connection.fetch(
                    """
                    SELECT collection_id, milestone
                    FROM trainer_collection_claims
                    WHERE trainer_id = $1
                    """,
                    trainer_id,
                )
        except UndefinedTableError as error:
            raise ValueError(_SCHEMA_ERROR) from error
        return frozenset((row["collection_id"], row["milestone"]) for row in rows)

    async def claim(
        self,
        trainer_id: int,
        collection_id: str,
        milestone: int,
        entry_identities: tuple[tuple[int, int | None], ...],
        candies: CandyBundle,
        mints: int,
    ) -> bool:
        try:
            return await self._claim(
                trainer_id,
                collection_id,
                milestone,
                entry_identities,
                candies,
                mints,
            )
        except UndefinedTableError as error:
            logger.error(
                "collection_claim_failed stage=schema trainer_id=%s collection=%s "
                "milestone=%s success=false",
                trainer_id,
                collection_id,
                milestone,
            )
            raise ValueError(_SCHEMA_ERROR) from error
        except Exception:
            logger.exception(
                "collection_claim_failed stage=persistence trainer_id=%s "
                "collection=%s milestone=%s candies=%s mints=%s success=false",
                trainer_id,
                collection_id,
                milestone,
                self._bundle_to_json(candies),
                mints,
            )
            raise

    async def _claim(
        self,
        trainer_id: int,
        collection_id: str,
        milestone: int,
        entry_identities: tuple[tuple[int, int | None], ...],
        candies: CandyBundle,
        mints: int,
    ) -> bool:
        pool = await get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("SELECT pg_advisory_xact_lock($1)", trainer_id)
                history_rows = await connection.fetch(
                    """
                    SELECT species_id, variant_id
                    FROM trainer_collection_entries
                    WHERE trainer_id = $1
                    """,
                    trainer_id,
                )
                owned_rows = await connection.fetch(
                    """
                    SELECT species_id, current_form_id
                    FROM creatures
                    WHERE trainer_id = $1
                    FOR SHARE
                    """,
                    trainer_id,
                )
                required = set(entry_identities)
                historical_count = len(
                    required
                    & {(row["species_id"], row["variant_id"]) for row in history_rows}
                )
                owned_count = len(
                    required
                    & {
                        (row["species_id"], row["current_form_id"])
                        for row in owned_rows
                    }
                )
                if historical_count < milestone:
                    raise ValueError("Collection milestone is not complete.")
                if owned_count < milestone:
                    raise ValueError(
                        "Collect the required entries in your current collection first."
                    )
                claim = await connection.fetchrow(
                    """
                    INSERT INTO trainer_collection_claims (
                        trainer_id, collection_id, milestone, progress,
                        rewarded_candies, rewarded_mints
                    )
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                    ON CONFLICT (trainer_id, collection_id, milestone) DO NOTHING
                    RETURNING collection_id
                    """,
                    trainer_id,
                    collection_id,
                    milestone,
                    historical_count,
                    json.dumps(self._bundle_to_json(candies)),
                    mints,
                )
                if claim is None:
                    return False

                rows = await connection.fetch(
                    """
                    SELECT candy_type, amount
                    FROM trainer_candies
                    WHERE trainer_id = $1
                    FOR UPDATE
                    """,
                    trainer_id,
                )
                inventory = self._candy_mapper.from_rows(rows)
                inventory.add(candies)
                await self._save_inventory(connection, trainer_id, inventory)
                if mints:
                    await connection.execute(
                        """
                        INSERT INTO trainer_mints (trainer_id, amount)
                        VALUES ($1, $2)
                        ON CONFLICT (trainer_id)
                        DO UPDATE SET amount = trainer_mints.amount + EXCLUDED.amount
                        """,
                        trainer_id,
                        mints,
                    )
        logger.info(
            "collection_claim trainer_id=%s collection=%s milestone=%s progress=%s "
            "candies=%s mints=%s success=true",
            trainer_id,
            collection_id,
            milestone,
            historical_count,
            self._bundle_to_json(candies),
            mints,
        )
        return True

    async def backfill_existing_creatures(self) -> int:
        try:
            pool = await get_pool()
            async with pool.acquire() as connection:
                result = await connection.execute("""
                    INSERT INTO trainer_collection_entries (
                        trainer_id, species_id, variant_id, source
                    )
                    SELECT trainer_id, species_id, current_form_id, 'backfill'
                    FROM creatures
                    WHERE trainer_id IS NOT NULL
                    ON CONFLICT DO NOTHING
                    """)
        except UndefinedTableError as error:
            raise ValueError(_SCHEMA_ERROR) from error
        return int(result.rsplit(" ", 1)[-1])

    async def _save_inventory(
        self, connection, trainer_id: int, inventory: CandyInventory
    ) -> None:
        await connection.execute(
            "DELETE FROM trainer_candies WHERE trainer_id = $1",
            trainer_id,
        )
        rows = self._candy_mapper.to_rows(inventory)
        if rows:
            await connection.executemany(
                """
                INSERT INTO trainer_candies (trainer_id, candy_type, amount)
                VALUES ($1, $2, $3)
                """,
                [(trainer_id, candy_type.value, amount) for candy_type, amount in rows],
            )

    @staticmethod
    def _bundle_to_json(bundle: CandyBundle) -> dict[str, int]:
        return {candy_type.value: amount for candy_type, amount in bundle.items()}
