import asyncio

from infrastructure.db_config import close_pool, get_pool

from .build_species import build_species
from .seed_species_neon import insert_species

TOTAL_SPECIES = 1025


async def main():
    pool = await get_pool()
    imported = 0

    async with pool.acquire() as conn:

        async with conn.transaction():

            for pokemon_id in range(1, TOTAL_SPECIES + 1):
                try:
                    species = build_species(pokemon_id)

                    await insert_species(conn, species)

                    imported += 1

                    print(f"[{pokemon_id}/{TOTAL_SPECIES}] " f"✔ {species['name']}")

                except Exception as e:
                    print(f"[{pokemon_id}] ERROR -> {e}")

    await close_pool()

    print(
        f"\n🎉 Importación finalizada. "
        f"{imported}/{TOTAL_SPECIES} especies procesadas."
    )


if __name__ == "__main__":
    asyncio.run(main())
