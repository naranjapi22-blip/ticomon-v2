from core.team.team_repository import TeamRepository
from core.team.team_slot import TeamSlot
from infrastructure.db_config import get_pool


class NeonTeamRepository(TeamRepository):
    """
    PostgreSQL implementation of TeamRepository.
    """

    async def get_by_trainer(
        self,
        trainer_id: int,
    ) -> list[TeamSlot]:
        pool = await get_pool()

        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT id, trainer_id, slot, creature_id
                FROM trainer_team_slots
                WHERE trainer_id = $1
                ORDER BY slot
                """,
                trainer_id,
            )

        return [
            TeamSlot(
                id=row["id"],
                trainer_id=row["trainer_id"],
                slot=row["slot"],
                creature_id=row["creature_id"],
            )
            for row in rows
        ]

    async def get_by_creature_id(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> TeamSlot | None:
        pool = await get_pool()

        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT id, trainer_id, slot, creature_id
                FROM trainer_team_slots
                WHERE trainer_id = $1
                  AND creature_id = $2
                """,
                trainer_id,
                creature_id,
            )

        if row is None:
            return None

        return TeamSlot(
            id=row["id"],
            trainer_id=row["trainer_id"],
            slot=row["slot"],
            creature_id=row["creature_id"],
        )

    async def count_by_trainer(
        self,
        trainer_id: int,
    ) -> int:
        pool = await get_pool()

        async with pool.acquire() as connection:
            return await connection.fetchval(
                """
                SELECT COUNT(*)
                FROM trainer_team_slots
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

    async def add(
        self,
        trainer_id: int,
        slot: int,
        creature_id: int,
    ) -> TeamSlot:
        pool = await get_pool()

        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO trainer_team_slots (
                    trainer_id,
                    slot,
                    creature_id
                )
                VALUES ($1, $2, $3)
                RETURNING id, trainer_id, slot, creature_id
                """,
                trainer_id,
                slot,
                creature_id,
            )

        return TeamSlot(
            id=row["id"],
            trainer_id=row["trainer_id"],
            slot=row["slot"],
            creature_id=row["creature_id"],
        )

    async def replace_creature(
        self,
        trainer_id: int,
        old_creature_id: int,
        new_creature_id: int,
    ) -> TeamSlot:
        pool = await get_pool()

        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                UPDATE trainer_team_slots
                SET creature_id = $3
                WHERE trainer_id = $1
                  AND creature_id = $2
                RETURNING id, trainer_id, slot, creature_id
                """,
                trainer_id,
                old_creature_id,
                new_creature_id,
            )

        if row is None:
            raise ValueError(
                f"Creature {old_creature_id} is not assigned to trainer {trainer_id}."
            )

        return TeamSlot(
            id=row["id"],
            trainer_id=row["trainer_id"],
            slot=row["slot"],
            creature_id=row["creature_id"],
        )

    async def remove_by_creature_id(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> None:
        pool = await get_pool()

        async with pool.acquire() as connection:
            await connection.execute(
                """
                DELETE FROM trainer_team_slots
                WHERE trainer_id = $1
                  AND creature_id = $2
                """,
                trainer_id,
                creature_id,
            )
