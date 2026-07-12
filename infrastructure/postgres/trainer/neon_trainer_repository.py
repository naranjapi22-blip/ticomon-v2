from core.trainer.repository import TrainerRepository
from core.trainer.trainer import Trainer
from infrastructure.db_config import get_pool
from infrastructure.postgres.trainer.trainer_mapper import TrainerMapper


class NeonTrainerRepository(TrainerRepository):
    """
    PostgreSQL implementation of TrainerRepository backed by Neon.
    """

    async def get(
        self,
        trainer_id: int,
    ) -> Trainer | None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT
                    trainer_id,
                    starter_creature_id,
                    started_at
                FROM trainers
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

        if row is None:
            return None

        return TrainerMapper.from_row(row)

    async def exists(
        self,
        trainer_id: int,
    ) -> bool:

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT 1
                FROM trainers
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

        return row is not None

    async def save(
        self,
        trainer: Trainer,
    ) -> None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            await connection.execute(
                """
                INSERT INTO trainers (
                    trainer_id,
                    starter_creature_id,
                    started_at
                )
                VALUES ($1, $2, $3)
                """,
                trainer.trainer_id,
                trainer.starter_creature_id,
                trainer.started_at.replace(tzinfo=None),
            )
