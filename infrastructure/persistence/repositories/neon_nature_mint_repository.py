from dataclasses import replace

from core.creature.creature_mapper import CreatureMapper
from core.creature.nature import Nature
from core.mint.nature_mint_inventory import NatureMintInventory
from core.mint.nature_mint_repository import NatureMintRepository
from infrastructure.db_config import get_pool


class NeonNatureMintRepository(NatureMintRepository):
    def __init__(self, species_repository) -> None:
        self._species_repository = species_repository
        self._mapper = CreatureMapper()

    async def get(self, trainer_id: int) -> NatureMintInventory:
        pool = await get_pool()
        async with pool.acquire() as connection:
            amount = await connection.fetchval(
                "SELECT amount FROM trainer_mints WHERE trainer_id = $1",
                trainer_id,
            )
        return NatureMintInventory(int(amount or 0))

    async def apply(
        self,
        trainer_id: int,
        collection_number: int,
        minted_nature: Nature | None,
    ):
        pool = await get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "SELECT pg_advisory_xact_lock($1)",
                    trainer_id,
                )
                row = await connection.fetchrow(
                    """
                    SELECT c.*, sv.id AS variant_id, sv.name AS variant_name
                    FROM creatures c
                    LEFT JOIN species_variants sv ON sv.id = c.current_form_id
                    WHERE c.trainer_id = $1 AND c.collection_number = $2
                    FOR UPDATE OF c
                    """,
                    trainer_id,
                    collection_number,
                )
                if row is None:
                    raise ValueError(f"Creature #{collection_number} was not found.")

                current_name = row["minted_nature"] or row["nature"]
                requested_name = minted_nature.name if minted_nature else row["nature"]
                if current_name == requested_name:
                    raise ValueError("Creature already has that nature effect.")

                amount = await connection.fetchval(
                    """
                    SELECT amount FROM trainer_mints
                    WHERE trainer_id = $1
                    FOR UPDATE
                    """,
                    trainer_id,
                )
                inventory = NatureMintInventory(int(amount or 0))
                inventory.consume_one()

                await connection.execute(
                    """
                    UPDATE creatures
                    SET minted_nature = $1
                    WHERE id = $2
                    """,
                    minted_nature.name if minted_nature else None,
                    row["id"],
                )
                updated_amount = await connection.fetchval(
                    """
                    UPDATE trainer_mints
                    SET amount = $1
                    WHERE trainer_id = $2
                    RETURNING amount
                    """,
                    inventory.amount,
                    trainer_id,
                )
                if updated_amount is None:
                    raise ValueError("Nature Mint inventory was not found.")

                updated_row = dict(row)
                updated_row["minted_nature"] = (
                    minted_nature.name if minted_nature else None
                )

        species = await self._species_repository.get(updated_row["species_id"])
        creature = self._mapper.from_row(updated_row, species)
        return replace(creature), int(updated_amount)
