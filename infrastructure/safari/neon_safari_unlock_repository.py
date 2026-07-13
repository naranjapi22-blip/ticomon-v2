from datetime import datetime
from uuid import UUID

from core.safari.unlock import SafariUnlock
from core.safari.unlock_repository import SafariUnlockRepository
from infrastructure.db_config import get_pool
from infrastructure.safari.unlock_mapper import SafariUnlockMapper


class NeonSafariUnlockRepository(SafariUnlockRepository):
    def __init__(self) -> None:
        self._mapper = SafariUnlockMapper()

    async def save(self, unlock: SafariUnlock) -> SafariUnlock:
        pool = await get_pool()

        async with pool.acquire() as connection:
            if unlock.id is None:
                row = await connection.fetchrow(
                    """
                    INSERT INTO safari_unlocks (
                        guild_id,
                        level,
                        encounter_count,
                        balls_per_participant,
                        map_influence,
                        status,
                        unlocked_at,
                        consumed_at,
                        consumed_session_id
                    )
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
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
                        map_influence = $5::jsonb,
                        status = $6,
                        unlocked_at = $7,
                        consumed_at = $8,
                        consumed_session_id = $9
                    WHERE id = $10
                    RETURNING *
                    """,
                    *self._mapper.to_row(unlock),
                    unlock.id,
                )

        if row is None:
            raise ValueError(f"Safari unlock {unlock.id} was not found.")

        return self._mapper.from_row(row)

    async def get_available_by_guild_id(
        self,
        guild_id: int,
    ) -> tuple[SafariUnlock, ...]:
        self._validate_guild_id(guild_id)
        pool = await get_pool()

        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT *
                FROM safari_unlocks
                WHERE guild_id = $1
                  AND status = 'AVAILABLE'
                ORDER BY unlocked_at, id
                """,
                guild_id,
            )

        return tuple(self._mapper.from_row(row) for row in rows)

    async def consume_next(
        self,
        guild_id: int,
        consumed_at: datetime,
        consumed_session_id: UUID,
    ) -> SafariUnlock | None:
        self._validate_guild_id(guild_id)
        if consumed_at is None or consumed_session_id is None:
            raise ValueError("consumption data is required.")

        pool = await get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """
                    WITH next_unlock AS (
                        SELECT id
                        FROM safari_unlocks
                        WHERE guild_id = $1
                          AND status = 'AVAILABLE'
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
                    guild_id,
                    self._mapper.as_utc(consumed_at),
                    consumed_session_id,
                )

        return self._mapper.from_row(row) if row is not None else None

    @staticmethod
    def _validate_guild_id(guild_id: int) -> None:
        if guild_id <= 0:
            raise ValueError("guild_id must be positive.")
