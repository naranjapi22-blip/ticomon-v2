from core.candy.candy_inventory import CandyInventory
from core.candy.candy_repository import CandyRepository
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.candy_mapper import (
    CandyMapper,
)


class NeonCandyRepository(CandyRepository):
    """
    PostgreSQL implementation of CandyRepository backed by Neon.
    """

    def __init__(
        self,
    ) -> None:
        self._mapper = CandyMapper()

    async def get(
        self,
        trainer_id: int,
    ) -> CandyInventory:

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT
                    candy_type,
                    amount
                FROM trainer_candies
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

        return self._mapper.from_rows(
            rows,
        )

    async def save(
        self,
        trainer_id: int,
        inventory: CandyInventory,
    ) -> None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            async with connection.transaction():

                await connection.execute(
                    """
                    DELETE
                    FROM trainer_candies
                    WHERE trainer_id = $1
                    """,
                    trainer_id,
                )

                for candy_type, amount in self._mapper.to_rows(
                    inventory,
                ):

                    await connection.execute(
                        """
                        INSERT INTO trainer_candies (
                            trainer_id,
                            candy_type,
                            amount
                        )
                        VALUES (
                            $1,
                            $2,
                            $3
                        )
                        """,
                        trainer_id,
                        candy_type.value,
                        amount,
                    )
