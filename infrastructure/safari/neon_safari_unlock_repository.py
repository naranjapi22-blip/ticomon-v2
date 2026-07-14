from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import asyncpg

from application.safari.exceptions import SafariUnlockAlreadyExists
from core.safari.unlock import SafariUnlock
from core.safari.unlock_repository import SafariUnlockRepository
from infrastructure.db_config import get_pool
from infrastructure.safari.unlock_mapper import SafariUnlockMapper


class NeonSafariUnlockRepository(SafariUnlockRepository):
    def __init__(self) -> None:
        self._mapper = SafariUnlockMapper()

    async def save(self, unlock: SafariUnlock) -> SafariUnlock:
        pool = await get_pool()

        try:
            async with pool.acquire() as connection:
                if unlock.id is None:
                    row = await connection.fetchrow(
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
                        *self._mapper.to_row(unlock),
                    )
                else:
                    row = await connection.fetchrow(
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
                        *self._mapper.to_row(unlock),
                        unlock.id,
                    )
        except asyncpg.UniqueViolationError as error:
            raise SafariUnlockAlreadyExists(
                "A Safari unlock for that level already exists today."
            ) from error

        if row is None:
            raise ValueError(f"Safari unlock {unlock.id} was not found.")

        return self._mapper.from_row(row)

    async def get_available_by_guild_id(
        self,
        guild_id: int,
        cycle_date: date | None = None,
    ) -> tuple[SafariUnlock, ...]:
        self._validate_guild_id(guild_id)
        pool = await get_pool()

        cycle_clause = ""
        parameters: tuple = (guild_id,)
        if cycle_date is not None:
            cycle_clause = "AND cycle_date = $2"
            parameters = (guild_id, cycle_date)

        async with pool.acquire() as connection:
            rows = await connection.fetch(
                f"""
                SELECT *
                FROM safari_unlocks
                WHERE guild_id = $1
                  AND status = 'AVAILABLE'
                  {cycle_clause}
                ORDER BY unlocked_at, id
                """,
                *parameters,
            )

        return tuple(self._mapper.from_row(row) for row in rows)

    async def consume_next(
        self,
        guild_id: int,
        consumed_at: datetime,
        consumed_session_id: UUID,
        cycle_date: date | None = None,
    ) -> SafariUnlock | None:
        self._validate_guild_id(guild_id)
        if consumed_at is None or consumed_session_id is None:
            raise ValueError("consumption data is required.")

        pool = await get_pool()

        cycle_clause = ""
        parameters: tuple = (
            guild_id,
            self._mapper.as_utc(consumed_at),
            consumed_session_id,
        )
        if cycle_date is not None:
            cycle_clause = "AND cycle_date = $4"
            parameters = (
                guild_id,
                self._mapper.as_utc(consumed_at),
                consumed_session_id,
                cycle_date,
            )

        async with pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    f"""
                    WITH next_unlock AS (
                        SELECT id
                        FROM safari_unlocks
                        WHERE guild_id = $1
                          AND status = 'AVAILABLE'
                          {cycle_clause}
                        ORDER BY unlocked_at, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE safari_unlocks AS unlock
                    SET
                        status = 'CONSUMED',
                        consumed_at = $2,
                        consumed_session_id = $3
                    FROM next_unlock
                    WHERE unlock.id = next_unlock.id
                    RETURNING unlock.*
                    """,
                    *parameters,
                )

        return self._mapper.from_row(row) if row is not None else None

    async def consume(
        self,
        unlock_id: int,
        guild_id: int,
        consumed_at: datetime,
        consumed_session_id: UUID,
    ) -> SafariUnlock | None:
        if unlock_id <= 0:
            raise ValueError("unlock_id must be positive.")
        self._validate_guild_id(guild_id)
        if consumed_at is None or consumed_session_id is None:
            raise ValueError("consumption data is required.")

        pool = await get_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                UPDATE safari_unlocks
                SET
                    status = 'CONSUMED',
                    consumed_at = $3,
                    consumed_session_id = $4
                WHERE id = $1
                  AND guild_id = $2
                  AND status = 'AVAILABLE'
                RETURNING *
                """,
                unlock_id,
                guild_id,
                self._mapper.as_utc(consumed_at),
                consumed_session_id,
            )

        return self._mapper.from_row(row) if row is not None else None

    async def expire_available_before(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> int:
        self._validate_guild_id(guild_id)
        if cycle_date is None:
            raise ValueError("cycle_date is required.")

        pool = await get_pool()
        async with pool.acquire() as connection:
            result = await connection.execute(
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

    @staticmethod
    def _validate_guild_id(guild_id: int) -> None:
        if guild_id <= 0:
            raise ValueError("guild_id must be positive.")
