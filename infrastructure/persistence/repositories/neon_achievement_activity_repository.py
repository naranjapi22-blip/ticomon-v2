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
            rows = await connection.fetch(
                """
                SELECT a.activity_type, s.type_1, s.type_2,
                       s.is_legendary, s.is_mythical, s.is_baby
                FROM trainer_achievement_activities AS a
                LEFT JOIN species AS s ON s.id = a.species_id
                WHERE a.trainer_id = $1
                """,
                trainer_id,
            )
        type_counts: dict[str, int] = {}
        capture_count = shiny_count = discovered = trade_count = safari_count = 0
        evolution_count = 0
        legendary = mythical = baby = 0
        for row in rows:
            activity_type = row["activity_type"]
            if activity_type == AchievementActivityType.CAPTURE.value:
                capture_count += 1
                legendary += int(bool(row["is_legendary"]))
                mythical += int(bool(row["is_mythical"]))
                baby += int(bool(row["is_baby"]))
                for species_type in (row["type_1"], row["type_2"]):
                    if species_type:
                        type_counts[species_type] = type_counts.get(species_type, 0) + 1
            elif activity_type == AchievementActivityType.SHINY_CAPTURE.value:
                shiny_count += 1
            elif activity_type == AchievementActivityType.SPECIES_DISCOVERED.value:
                discovered += 1
            elif activity_type == AchievementActivityType.COMPLETED_TRADE.value:
                trade_count += 1
            elif activity_type == AchievementActivityType.SAFARI_CAPTURE.value:
                safari_count += 1
            elif activity_type == AchievementActivityType.EVOLUTION.value:
                evolution_count += 1
        return AchievementProgress(
            capture_count=capture_count,
            shiny_capture_count=shiny_count,
            unique_discovered_species=discovered,
            completed_trade_count=trade_count,
            safari_capture_count=safari_count,
            legendary_capture_count=legendary,
            mythical_capture_count=mythical,
            baby_capture_count=baby,
            evolution_count=evolution_count,
            capture_counts_by_type=type_counts,
        )
