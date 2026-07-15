import logging
from pathlib import Path

from infrastructure.db_config import close_pool, get_pool

BASE_DIR = Path(__file__).resolve().parent.parent
VARIANTS_FOLDER = BASE_DIR / "showdown_variants"

# Showdown uses a different folder name from the base Species.
SPECIES_NAME_MAP = {
    "oricorio": "oricorio-baile",
    "toxtricity": "toxtricity-amped",
    "morpeko": "morpeko-full-belly",
    "eiscue": "eiscue-ice",
    "minior": "minior-red-meteor",
    "squawkabilly": "squawkabilly-green-plumage",
    "tatsugiri": "tatsugiri-curly",
}

logger = logging.getLogger(__name__)


async def main():

    pool = await get_pool()

    imported = 0
    duplicates = 0
    missing_species = 0

    async with pool.acquire() as connection:

        for species_folder in sorted(VARIANTS_FOLDER.iterdir()):

            if not species_folder.is_dir():
                continue

            species_name = SPECIES_NAME_MAP.get(
                species_folder.name.lower(),
                species_folder.name.lower(),
            )

            species = await connection.fetchrow(
                """
                SELECT id
                FROM species
                WHERE LOWER(name) = $1
                """,
                species_name,
            )

            if species is None:
                logger.warning("Species not found: %s", species_name)
                missing_species += 1
                continue

            species_id = species["id"]

            for file in sorted(species_folder.iterdir()):

                if not file.is_file():
                    continue

                stem = file.stem

                if "-" not in stem:
                    logger.warning("Skipping invalid filename: %s", file.name)
                    continue

                variant_name = stem.split("-", 1)[1]

                inserted = await connection.execute(
                    """
                    INSERT INTO species_variants (
                        species_id,
                        name
                    )
                    VALUES (
                        $1,
                        $2
                    )
                    ON CONFLICT DO NOTHING
                    """,
                    species_id,
                    variant_name,
                )

                if inserted == "INSERT 0 1":
                    imported += 1
                else:
                    duplicates += 1

    await close_pool()

    logger.info("%s", "=" * 40)
    logger.info("Imported variants : %s", imported)
    logger.info("Duplicates        : %s", duplicates)
    logger.info("Missing species   : %s", missing_species)
    logger.info("%s", "=" * 40)


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
