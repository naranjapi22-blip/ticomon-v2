from core.energy.repository import EnergyRepository
from core.energy.trainer_energy import TrainerEnergy
from infrastructure.db_config import get_pool
from infrastructure.postgres.energy.energy_mapper import EnergyMapper


class NeonEnergyRepository(EnergyRepository):
    """
    PostgreSQL implementation of EnergyRepository backed by Neon.
    """

    async def get(
        self,
        trainer_id: int,
    ) -> TrainerEnergy | None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT
                    trainer_id,
                    current_energy,
                    max_energy,
                    last_regenerated_at
                FROM trainer_energy
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

        if row is None:
            return None

        return EnergyMapper.to_domain(row)

    async def save(
        self,
        energy: TrainerEnergy,
    ) -> None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            await connection.execute(
                """
                INSERT INTO trainer_energy (
                    trainer_id,
                    current_energy,
                    max_energy,
                    last_regenerated_at
                )
                VALUES ($1, $2, $3, $4)
                """,
                energy.trainer_id,
                energy.current_energy,
                energy.max_energy,
                energy.last_regenerated_at.replace(tzinfo=None),
            )

    async def update(
        self,
        energy: TrainerEnergy,
    ) -> None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            await connection.execute(
                """
                UPDATE trainer_energy
                SET
                    current_energy = $2,
                    last_regenerated_at = $3
                WHERE trainer_id = $1
                """,
                energy.trainer_id,
                energy.current_energy,
                energy.last_regenerated_at.replace(tzinfo=None),
            )
