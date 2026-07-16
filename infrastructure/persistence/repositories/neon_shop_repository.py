import logging

from asyncpg.exceptions import UndefinedTableError

from core.candy.candy_inventory import CandyInventory
from core.creature.creature_mapper import CreatureMapper
from core.shop.repository import ShopRepository
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.candy_mapper import CandyMapper

logger = logging.getLogger(__name__)


class NeonShopRepository(ShopRepository):
    def __init__(self, species_repository) -> None:
        self._species_repository = species_repository
        self._creature_mapper = CreatureMapper()
        self._candy_mapper = CandyMapper()

    async def purchase(
        self,
        trainer_id,
        creature,
        cost,
        product_id,
        idempotency_key,
    ):
        try:
            result = await self._purchase(
                trainer_id, creature, cost, product_id, idempotency_key
            )
        except Exception as error:
            variant = creature.current_form
            variant_name = variant.name if variant is not None else None
            cream = decoration = None
            if (
                variant_name
                and "-" in variant_name
                and creature.species.name.lower() == "alcremie"
            ):
                cream, decoration = variant_name.rsplit("-", 1)
            logger.exception(
                "shop_purchase_failed stage=persistence trainer_id=%s shop=%s "
                "product=%s species_id=%s variant_id=%s cream=%s decoration=%s "
                "costs=%s idempotency_key=%s success=false",
                trainer_id,
                creature.species.name,
                product_id,
                creature.species.id,
                variant.id if variant is not None else None,
                cream,
                decoration,
                {candy_type.value: amount for candy_type, amount in cost.items()},
                idempotency_key,
            )
            if isinstance(error, UndefinedTableError):
                if "trainer_collection_entries" in str(error):
                    raise ValueError(
                        "Collections schema is not initialized. "
                        "Run scripts/create_collection_schema.py."
                    ) from error
                raise ValueError(
                    "Shop schema is not initialized. Run scripts/create_shop_schema.py."
                ) from error
            raise
        logger.info(
            "shop_purchase trainer_id=%s product=%s creature_id=%s "
            "costs=%s success=true",
            trainer_id,
            product_id,
            result[0].id,
            {candy_type.value: amount for candy_type, amount in cost.items()},
        )
        return result

    async def _purchase(
        self,
        trainer_id,
        creature,
        cost,
        product_id,
        idempotency_key,
    ):
        pool = await get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "SELECT pg_advisory_xact_lock($1)",
                    trainer_id,
                )
                receipt = await connection.fetchrow(
                    """
                    SELECT trainer_id, product_id, creature_id
                    FROM shop_purchase_receipts
                    WHERE idempotency_key = $1
                    FOR SHARE
                    """,
                    idempotency_key,
                )
                if receipt is not None:
                    if (
                        receipt["trainer_id"] != trainer_id
                        or receipt["product_id"] != product_id
                    ):
                        raise ValueError("Shop purchase idempotency key was reused.")
                    row = await self._creature_row(connection, receipt["creature_id"])
                    inventory = await self._inventory(connection, trainer_id)
                    species = await self._species_repository.get(row["species_id"])
                    return (
                        self._creature_mapper.from_row(row, species),
                        inventory,
                        False,
                    )

                inventory = await self._inventory(connection, trainer_id)
                inventory.consume(cost)
                await self._lock_collection_number(connection, trainer_id)
                collection_number = await connection.fetchval(
                    """
                    SELECT COALESCE(MAX(collection_number), 0) + 1
                    FROM creatures
                    WHERE trainer_id = $1
                    """,
                    trainer_id,
                )
                params = self._creature_mapper.to_row(creature)
                created = await connection.fetchrow(
                    """
                    INSERT INTO creatures (
                        trainer_id, original_trainer_id, collection_number,
                        species_id, current_form_id, is_shiny, nature, size,
                        hp_iv, attack_iv, defense_iv, special_attack_iv,
                        special_defense_iv, speed_iv, minted_nature
                    )
                    VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14, $15
                    )
                    RETURNING id
                    """,
                    params[0],
                    params[1],
                    collection_number,
                    *params[2:],
                )
                await connection.execute(
                    """
                    INSERT INTO trainer_collection_entries (
                        trainer_id, species_id, variant_id, source
                    )
                    VALUES ($1, $2, $3, 'shop')
                    ON CONFLICT DO NOTHING
                    """,
                    trainer_id,
                    creature.species.id,
                    (
                        creature.current_form.id
                        if creature.current_form is not None
                        else None
                    ),
                )
                for candy_type, amount in cost.items():
                    command = await connection.execute(
                        """
                        UPDATE trainer_candies
                        SET amount = amount - $3
                        WHERE trainer_id = $1
                          AND candy_type = $2
                          AND amount >= $3
                        """,
                        trainer_id,
                        candy_type.value,
                        amount,
                    )
                    if command != "UPDATE 1":
                        raise ValueError("Candy balance changed during purchase.")
                await connection.execute(
                    """
                    INSERT INTO shop_purchase_receipts (
                        idempotency_key, trainer_id, product_id, creature_id
                    )
                    VALUES ($1, $2, $3, $4)
                    """,
                    idempotency_key,
                    trainer_id,
                    product_id,
                    created["id"],
                )
                row = await self._creature_row(connection, created["id"])

            species = await self._species_repository.get(row["species_id"])
            return self._creature_mapper.from_row(row, species), inventory, True

    async def _inventory(self, connection, trainer_id: int) -> CandyInventory:
        rows = await connection.fetch(
            """
            SELECT candy_type, amount
            FROM trainer_candies
            WHERE trainer_id = $1
            FOR UPDATE
            """,
            trainer_id,
        )
        return self._candy_mapper.from_rows(rows)

    @staticmethod
    async def _lock_collection_number(connection, trainer_id: int) -> None:
        await connection.execute(
            "SELECT pg_advisory_xact_lock($1)",
            trainer_id,
        )

    @staticmethod
    async def _creature_row(connection, creature_id: int):
        row = await connection.fetchrow(
            """
            SELECT c.*, sv.id AS variant_id, sv.name AS variant_name
            FROM creatures c
            LEFT JOIN species_variants sv ON sv.id = c.current_form_id
            WHERE c.id = $1
            """,
            creature_id,
        )
        if row is None:
            raise ValueError("Purchased creature was not found.")
        return row
