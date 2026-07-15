from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, date, datetime

from core.achievement.activity import AchievementActivity
from core.candy.candy_inventory import CandyInventory
from core.capture.application.capture_unit_of_work import (
    CaptureTransaction,
    CaptureUnitOfWork,
    SaveUnlockResult,
)
from core.creature.creature import Creature
from core.creature.creature_mapper import CreatureMapper
from core.safari.daily_progress import SafariDailyWorld
from core.safari.unlock import SafariUnlock
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.candy_mapper import CandyMapper
from infrastructure.safari.daily_world_mapper import SafariDailyWorldMapper
from infrastructure.safari.unlock_mapper import SafariUnlockMapper


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
        self._daily_world_mapper = SafariDailyWorldMapper()
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

    async def record_achievement_activity(self, activity: AchievementActivity) -> bool:
        row = await self._connection.fetchrow(
            """
            INSERT INTO trainer_achievement_activities (
                trainer_id, activity_type, species_id, source, occurred_at,
                idempotency_key
            )
            VALUES ($1, $2, $3, $4, COALESCE($5, NOW()), $6)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            activity.trainer_id,
            activity.activity_type.value,
            activity.species_id,
            activity.source.value if activity.source else None,
            activity.occurred_at,
            activity.idempotency_key,
        )
        return row is not None

    async def get_or_create_daily_world(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> SafariDailyWorld:
        await self._connection.execute(
            """
            INSERT INTO safari_daily_worlds (
                guild_id,
                cycle_date,
                daily_capture_count,
                daily_unlock_count,
                current_influence
            )
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (guild_id, cycle_date) DO NOTHING
            """,
            *self._daily_world_mapper.to_row(
                SafariDailyWorld.create(guild_id, cycle_date)
            ),
        )
        row = await self._connection.fetchrow(
            """
            SELECT *
            FROM safari_daily_worlds
            WHERE guild_id = $1
              AND cycle_date = $2
            FOR UPDATE
            """,
            guild_id,
            cycle_date,
        )
        assert row is not None
        return self._daily_world_mapper.from_row(row)

    async def save_daily_world(self, world: SafariDailyWorld) -> None:
        await self._connection.execute(
            """
            INSERT INTO safari_daily_worlds (
                guild_id,
                cycle_date,
                daily_capture_count,
                daily_unlock_count,
                current_influence
            )
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (guild_id, cycle_date) DO UPDATE
            SET
                daily_capture_count = EXCLUDED.daily_capture_count,
                daily_unlock_count = EXCLUDED.daily_unlock_count,
                current_influence = EXCLUDED.current_influence
            """,
            *self._daily_world_mapper.to_row(world),
        )

    async def register_daily_active_trainer_if_absent(
        self,
        guild_id: int,
        cycle_date: date,
        trainer_id: int,
        first_capture_at: datetime,
    ) -> bool:
        row = await self._connection.fetchrow(
            """
            INSERT INTO safari_daily_active_trainers (
                guild_id,
                cycle_date,
                trainer_id,
                first_capture_at
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, cycle_date, trainer_id) DO NOTHING
            RETURNING trainer_id
            """,
            guild_id,
            cycle_date,
            trainer_id,
            (
                first_capture_at.astimezone(UTC)
                if first_capture_at.tzinfo is not None
                else first_capture_at.replace(tzinfo=UTC)
            ),
        )
        return row is not None

    async def count_daily_active_trainers(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> int:
        value = await self._connection.fetchval(
            """
            SELECT COUNT(*)
            FROM safari_daily_active_trainers
            WHERE guild_id = $1
              AND cycle_date = $2
            """,
            guild_id,
            cycle_date,
        )
        return int(value or 0)

    async def expire_available_unlocks_before(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> int:
        result = await self._connection.execute(
            """
            UPDATE safari_unlocks
            SET status = 'EXPIRED'
            WHERE guild_id = $1
              AND cycle_date < $2
              AND status = 'AVAILABLE'
            """,
            guild_id,
            cycle_date,
        )
        return int(result.split()[-1]) if result else 0

    async def save_unlock(self, unlock: SafariUnlock) -> SaveUnlockResult:
        if unlock.id is not None:
            row = await self._connection.fetchrow(
                """
                UPDATE safari_unlocks
                SET
                    guild_id = $1,
                    level = $2,
                    encounter_count = $3,
                    balls_per_participant = $4,
                    cycle_date = $5,
                    map_influence = $6::jsonb,
                    status = $7,
                    unlocked_at = $8,
                    consumed_at = $9,
                    consumed_session_id = $10
                WHERE id = $11
                RETURNING *
                """,
                *self._unlock_mapper.to_row(unlock),
                unlock.id,
            )
            if row is None:
                raise ValueError(f"Safari unlock {unlock.id} was not found.")
            return SaveUnlockResult(self._unlock_mapper.from_row(row), created=False)

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
            ON CONFLICT (guild_id, cycle_date, level) DO NOTHING
            RETURNING *
            """,
            *self._unlock_mapper.to_row(unlock),
        )
        created = row is not None
        if row is None:
            row = await self._connection.fetchrow(
                """
                SELECT *
                FROM safari_unlocks
                WHERE guild_id = $1
                  AND cycle_date = $2
                  AND level = $3
                """,
                unlock.guild_id,
                (
                    unlock.cycle_date
                    or self._unlock_mapper.as_utc(unlock.unlocked_at).date()
                ),
                unlock.level,
            )
        if row is None:
            raise ValueError(
                "Safari unlock was not found after insert or conflict resolution."
            )

        return SaveUnlockResult(self._unlock_mapper.from_row(row), created=created)
