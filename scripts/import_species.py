import asyncio
import csv
import logging

from core.species.regional_species import (
    REGIONAL_POKEAPI_IDS,
    is_regional_pokeapi_id,
)
from infrastructure.db_config import close_pool, get_pool

from .seed_species_neon import insert_species

CSV_FILE = "pokemon_data.csv"

logger = logging.getLogger(__name__)


def get_base_name(name: str) -> str:
    """
    Returns the base species name for a regional form.
    """

    if name.startswith("mr-mime-"):
        return "mr-mime"

    return name.split("-")[0]


def build_species(
    row: dict,
    spawn_rarity: str,
) -> dict:
    return {
        "pokeapi_id": int(row["pokeapi_id"]),
        "name": row["name"],
        "types": row["types"].split(","),
        "height": float(row["height"]),
        "weight": float(row["weight"]),
        "display_scale": float(row["display_scale"]),
        "capture_rate": int(row["capture_rate"]),
        "spawn_rarity": spawn_rarity,
        "generation": 0,
        "is_baby": False,
        "is_legendary": str(row["is_legendary"]).lower() == "true",
        "is_mythical": str(row["is_mythical"]).lower() == "true",
        "base_stats": {
            "hp": int(row["hp"]),
            "attack": int(row["attack"]),
            "defense": int(row["defense"]),
            "special_attack": int(row["special_attack"]),
            "special_defense": int(row["special_defense"]),
            "speed": int(row["speed"]),
        },
    }


def is_regional_row(row: dict) -> bool:
    return is_regional_pokeapi_id(int(row["pokeapi_id"]))


async def main():
    pool = await get_pool()
    imported = 0

    async with pool.acquire() as conn:

        async with conn.transaction():

            with open(CSV_FILE, encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:

                    if not is_regional_row(row):
                        continue

                    base_name = get_base_name(row["name"])

                    spawn_rarity = await conn.fetchval(
                        """
                        SELECT spawn_rarity
                        FROM species
                        WHERE LOWER(name) = LOWER($1)
                        LIMIT 1
                        """,
                        base_name,
                    )

                    if spawn_rarity is None:
                        raise ValueError(f"Base species not found for {row['name']}")

                    species = build_species(
                        row,
                        spawn_rarity,
                    )

                    await insert_species(
                        conn,
                        species,
                    )

                    imported += 1

                    logger.info(
                        "[%s/%s] ✔ %s",
                        imported,
                        len(REGIONAL_POKEAPI_IDS),
                        species["name"],
                    )

    await close_pool()

    logger.info(
        "\n🎉 Import completed.\n%s regional forms imported.",
        imported,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
