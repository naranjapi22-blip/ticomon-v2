from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import date

from core.candy.candy_inventory import CandyInventory
from core.capture.application.capture_unit_of_work import (
    CaptureTransaction,
    CaptureUnitOfWork,
)
from core.creature.creature import Creature
from core.creature.creature_mapper import CreatureMapper
from core.safari.unlock import SafariUnlock
from core.safari.world import SafariWorld
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.candy_mapper import CandyMapper
from infrastructure.safari.unlock_mapper import SafariUnlockMapper
from infrastructure.safari.world_mapper import SafariWorldMapper


class NeonCaptureUnitOfWork(CaptureUnitOfWork):
    @asynccontextmanager
    async def transaction(self):
        pool = await get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                yield _NeonCaptureTransaction(connection)


class _NeonCaptureTransaction(CaptureTransaction):
    def __init__(self, connection) -> None:
        self._connection = connection
        self._creature_mapper = CreatureMapper()
        self._candy_mapper = CandyMapper()
        self._world_mapper = SafariWorldMapper()
        self._unlock_mapper = SafariUnlockMapper()

    async def save_creature(self, creature: Creature) -> Creature:
        if creature.trainer_id is None or creature.trainer_id <= 0:
            raise ValueError("Captured creature requires a valid trainer_id.")

        await self._connection.execute(
            "SELECT pg_advisory_xact_lock($1)",
            creature.trainer_id,
        )
        collection_number = await self._connection.fetchval(
            """
            SELECT COALESCE(MAX(collection_number), 0) + 1
            FROM creatures
            WHERE trainer_id = $1
            """,
            creature.trainer_id,
        )
        params = self._creature_mapper.to_row(creature)
        row = await self._connection.fetchrow(
            """
            INSERT INTO creatures (
                trainer_id,
                original_trainer_id,
                collection_number,
                species_id,
                current_form_id,
                is_shiny,
                nature,
                size,
                hp_iv,
                attack_iv,
                defense_iv,
                special_attack_iv,
                special_defense_iv,
                speed_iv
            )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7,
                    $8, $9, $10, $11, $12, $13, $14
                )
                RETURNING id, collection_number
                """,
            params[0],
            params[1],
            collection_number,
            *params[2:],
        )

        assert row is not None
        return replace(
            creature,
            id=row["id"],
            collection_number=row["collection_number"],
        )

    async def get_candy_inventory(self, trainer_id: int) -> CandyInventory:
        rows = await self._connection.fetch(
            """
            SELECT candy_type, amount
            FROM trainer_candies
            WHERE trainer_id = $1
            FOR UPDATE
            """,
            trainer_id,
        )
        return self._candy_mapper.from_rows(rows)

    async def save_candy_inventory(
        self,
        trainer_id: int,
        inventory: CandyInventory,
    ) -> None:
        await self._connection.execute(
            "DELETE FROM trainer_candies WHERE trainer_id = $1",
            trainer_id,
        )
        rows = self._candy_mapper.to_rows(inventory)

        if rows:
            await self._connection.executemany(
                """
                INSERT INTO trainer_candies (
                    trainer_id,
                    candy_type,
                    amount
                )
                VALUES ($1, $2, $3)
                """,
                [(trainer_id, candy_type.value, amount) for candy_type, amount in rows],
            )

    async def get_or_create_world(
        self,
        guild_id: int,
        reset_date: date,
    ) -> SafariWorld:
        initial_world = SafariWorld.create(guild_id, reset_date)
        await self._connection.execute(
            """
            INSERT INTO safari_worlds (
                guild_id,
                current_progress,
                daily_unlock_count,
                current_influence,
                last_daily_reset_date
            )
            VALUES ($1, $2, $3, $4::jsonb, $5)
            ON CONFLICT (guild_id) DO NOTHING
            """,
            *self._world_mapper.to_row(initial_world),
        )
        row = await self._connection.fetchrow(
            """
            SELECT *
            FROM safari_worlds
            WHERE guild_id = $1
            FOR UPDATE
            """,
            guild_id,
        )

        assert row is not None
        return self._world_mapper.from_row(row)

    async def save_world(self, world: SafariWorld) -> SafariWorld:
        row = await self._connection.fetchrow(
            """
            UPDATE safari_worlds
            SET
                current_progress = $2,
                daily_unlock_count = $3,
                current_influence = $4::jsonb,
                last_daily_reset_date = $5
            WHERE guild_id = $1
            RETURNING *
            """,
            *self._world_mapper.to_row(world),
        )

        if row is None:
            raise ValueError(f"Safari World for guild {world.guild_id} was not found.")
        return self._world_mapper.from_row(row)

    async def save_unlock(self, unlock: SafariUnlock) -> SafariUnlock:
        if unlock.id is not None:
            raise ValueError("New Safari unlocks cannot already have an id.")

        row = await self._connection.fetchrow(
            """
            INSERT INTO safari_unlocks (
                guild_id,
                level,
                encounter_count,
                balls_per_participant,
                cycle_date,
                map_influence,
                status,
                unlocked_at,
                consumed_at,
                consumed_session_id
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10)
            RETURNING *
            """,
            *self._unlock_mapper.to_row(unlock),
        )

        assert row is not None
        return self._unlock_mapper.from_row(row)
