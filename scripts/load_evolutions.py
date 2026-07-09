import csv
from pathlib import Path

from infrastructure.db_config import get_pool

CSV_PATH = Path("pokemon_evolutions(1).csv")


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
                    print(
                        "Missing:",
                        from_name,
                        "->",
                        to_name,
                    )

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

        print(f"Inserted: {inserted}")

        print(f"Skipped: {skipped}")


if __name__ == "__main__":

    import asyncio

    asyncio.run(load_evolutions())
