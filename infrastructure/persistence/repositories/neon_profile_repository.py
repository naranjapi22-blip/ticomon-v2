from core.profile.profile_repository import ProfileRepository
from infrastructure.db_config import get_pool


class NeonProfileRepository(ProfileRepository):
    """
    PostgreSQL implementation of ProfileRepository.
    """

    async def get_featured_creature_id(
        self,
        trainer_id: int,
    ) -> int | None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            return await connection.fetchval(
                """
                SELECT featured_creature_id
                FROM trainer_profiles
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

    async def set_featured_creature(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            await connection.execute(
                """
                INSERT INTO trainer_profiles (
                    trainer_id,
                    featured_creature_id
                )
                VALUES ($1, $2)
                ON CONFLICT (trainer_id)
                DO UPDATE SET
                    featured_creature_id = EXCLUDED.featured_creature_id
                """,
                trainer_id,
                creature_id,
            )
