import json
from datetime import datetime

from application.achievement.contracts import (
    AchievementUnlock,
    AchievementUnlockRepository,
)
from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.candy_mapper import CandyMapper


class NeonAchievementUnlockRepository(AchievementUnlockRepository):
    def __init__(self) -> None:
        self._candy_mapper = CandyMapper()

    async def get_by_trainer(self, trainer_id: int) -> tuple[AchievementUnlock, ...]:
        pool = await get_pool()

        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT trainer_id, achievement_id, unlocked_at, rewarded_candies
                FROM trainer_achievement_unlocks
                WHERE trainer_id = $1
                ORDER BY unlocked_at, achievement_id
                """,
                trainer_id,
            )
        return tuple(self._unlock_from_row(row) for row in rows)

    async def award(
        self,
        trainer_id: int,
        achievement_id: str,
        rewarded_candies: CandyBundle,
        unlocked_at: datetime,
    ) -> bool:
        pool = await get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "SELECT pg_advisory_xact_lock($1)",
                    trainer_id,
                )
                created = await connection.fetchrow(
                    """
                    INSERT INTO trainer_achievement_unlocks (
                        trainer_id,
                        achievement_id,
                        unlocked_at,
                        rewarded_candies
                    )
                    VALUES ($1, $2, $3, $4::jsonb)
                    ON CONFLICT (trainer_id, achievement_id)
                    DO NOTHING
                    RETURNING achievement_id
                    """,
                    trainer_id,
                    achievement_id,
                    unlocked_at,
                    json.dumps(self._bundle_to_json(rewarded_candies)),
                )
                if created is None:
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
                inventory.add(rewarded_candies)
                await connection.execute(
                    "DELETE FROM trainer_candies WHERE trainer_id = $1",
                    trainer_id,
                )
                await connection.executemany(
                    """
                    INSERT INTO trainer_candies (trainer_id, candy_type, amount)
                    VALUES ($1, $2, $3)
                    """,
                    [
                        (trainer_id, candy_type.value, amount)
                        for candy_type, amount in self._candy_mapper.to_rows(inventory)
                    ],
                )
        return True

    @staticmethod
    def _bundle_to_json(bundle: CandyBundle) -> dict[str, int]:
        return {candy_type.value: amount for candy_type, amount in bundle.items()}

    @staticmethod
    def _unlock_from_row(row) -> AchievementUnlock:
        rewarded_candies = row["rewarded_candies"]
        if isinstance(rewarded_candies, str):
            rewarded_candies = json.loads(rewarded_candies)
        rewarded_candies = CandyBundle.from_amounts(
            *(
                CandyAmount(CandyType(candy_type), amount)
                for candy_type, amount in rewarded_candies.items()
            )
        )
        return AchievementUnlock(
            trainer_id=row["trainer_id"],
            achievement_id=row["achievement_id"],
            unlocked_at=row["unlocked_at"],
            rewarded_candies=rewarded_candies,
        )
