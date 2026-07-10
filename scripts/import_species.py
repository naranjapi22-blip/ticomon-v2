import asyncio
import csv

from infrastructure.db_config import close_pool, get_pool

from .seed_species_neon import insert_species

CSV_FILE = "pokemon_data.csv"

START_ID = 1026
END_ID = 1077


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
        "name": row["nombre"],
        "types": row["tipos"].split(","),
        "height": float(row["height"]),
        "weight": float(row["weight"]),
        "display_scale": float(row["display_scale"]),
        "capture_rate": int(row["capture_rate"]),
        "spawn_rarity": spawn_rarity,
        "generation": 0,
        "is_baby": False,
        "is_legendary": str(row["es_legendario"]).lower() == "true",
        "is_mythical": str(row["es_mitico"]).lower() == "true",
        "base_stats": {
            "hp": int(row["hp"]),
            "attack": int(row["attack"]),
            "defense": int(row["defense"]),
            "special_attack": int(row["special_attack"]),
            "special_defense": int(row["special_defense"]),
            "speed": int(row["speed"]),
        },
    }


async def main():
    pool = await get_pool()
    imported = 0

    async with pool.acquire() as conn:

        async with conn.transaction():

            with open(CSV_FILE, encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:

                    species_id = int(row["id"])

                    if species_id < START_ID or species_id > END_ID:
                        continue

                    base_name = get_base_name(row["nombre"])

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
                        raise ValueError(
                            f"No se encontró la especie base para {row['nombre']}"
                        )

                    species = build_species(
                        row,
                        spawn_rarity,
                    )

                    await insert_species(
                        conn,
                        species,
                    )

                    imported += 1

                    print(f"[{species_id}/{END_ID}] ✔ {species['name']}")

    await close_pool()

    print(f"\n🎉 Importación finalizada." f"\n{imported} formas regionales importadas.")


if __name__ == "__main__":
    asyncio.run(main())
