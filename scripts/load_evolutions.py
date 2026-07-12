import csv
import logging
from pathlib import Path

from infrastructure.db_config import get_pool

CSV_PATH = Path("pokemon_evolutions(1).csv")

logger = logging.getLogger(__name__)


async def load_evolutions():

    pool = await get_pool()

    async with pool.acquire() as connection:

        inserted = 0
        skipped = 0

        with CSV_PATH.open(
            encoding="utf-8",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                from_name = row["pokemon_nombre"].strip().lower()

                to_name = row["evoluciona_a"].strip().lower()

                candy_type = row["tipo_caramelo"].strip().lower()

                tier = row["tier"].strip().lower()

                from_species = await connection.fetchrow(
                    """
                    SELECT id
                    FROM species
                    WHERE name = $1
                    """,
                    from_name,
                )

                to_species = await connection.fetchrow(
                    """
                    SELECT id
                    FROM species
                    WHERE name = $1
                    """,
                    to_name,
                )

                if from_species is None or to_species is None:
                    logger.warning("Missing: %s -> %s", from_name, to_name)

                    skipped += 1
                    continue

                await connection.execute(
                    """
                    INSERT INTO pokemon_evolutions
                    (
                        from_species_id,
                        to_species_id,
                        candy_type,
                        tier
                    )
                    VALUES
                    (
                        $1,
                        $2,
                        $3,
                        $4
                    )
                    """,
                    from_species["id"],
                    to_species["id"],
                    candy_type,
                    tier,
                )

                inserted += 1

        logger.info("Inserted: %s", inserted)
        logger.info("Skipped: %s", skipped)


if __name__ == "__main__":

    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(load_evolutions())
