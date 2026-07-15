from application.achievement.contracts import (
    AchievementActivityRepository,
    AchievementProgress,
)
from core.achievement.activity import AchievementActivity, AchievementActivityType
from infrastructure.db_config import get_pool


class NeonAchievementActivityRepository(AchievementActivityRepository):
    async def record(self, activity: AchievementActivity) -> bool:
        pool = await get_pool()

        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO trainer_achievement_activities (
                    trainer_id,
                    activity_type,
                    species_id,
                    source,
                    occurred_at,
                    idempotency_key
                )
                VALUES ($1, $2, $3, $4, COALESCE($5, NOW()), $6)
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                activity.trainer_id,
                activity.activity_type.value,
                activity.species_id,
                activity.source.value if activity.source is not None else None,
                activity.occurred_at,
                activity.idempotency_key,
            )
        return row is not None

    async def get_progress(self, trainer_id: int) -> AchievementProgress:
        pool = await get_pool()

        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE activity_type = $2
                    ) AS capture_count,
                    COUNT(*) FILTER (
                        WHERE activity_type = $3
                    ) AS shiny_capture_count,
                    COUNT(*) FILTER (
                        WHERE activity_type = $4
                    ) AS unique_discovered_species,
                    COUNT(*) FILTER (
                        WHERE activity_type = $5
                    ) AS completed_trade_count,
                    COUNT(*) FILTER (
                        WHERE activity_type = $6
                    ) AS safari_capture_count
                FROM trainer_achievement_activities
                WHERE trainer_id = $1
                """,
                trainer_id,
                AchievementActivityType.CAPTURE.value,
                AchievementActivityType.SHINY_CAPTURE.value,
                AchievementActivityType.SPECIES_DISCOVERED.value,
                AchievementActivityType.COMPLETED_TRADE.value,
                AchievementActivityType.SAFARI_CAPTURE.value,
            )
        assert row is not None
        return AchievementProgress(
            capture_count=row["capture_count"],
            shiny_capture_count=row["shiny_capture_count"],
            unique_discovered_species=row["unique_discovered_species"],
            completed_trade_count=row["completed_trade_count"],
            safari_capture_count=row["safari_capture_count"],
        )
