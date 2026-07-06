from infrastructure.db_config import get_connection

from .build_species import build_species
from .seed_species_neon import insert_species

TOTAL_SPECIES = 1025


def main():
    conn = get_connection()
    imported = 0

    try:
        for pokemon_id in range(1, TOTAL_SPECIES + 1):
            try:
                species = build_species(pokemon_id)
                insert_species(conn, species)

                imported += 1

                print(f"[{pokemon_id}/{TOTAL_SPECIES}] " f"✔ {species['name']}")

            except Exception as e:
                print(f"[{pokemon_id}] ERROR -> {e}")

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    print(
        f"\n🎉 Importación finalizada. "
        f"{imported}/{TOTAL_SPECIES} especies procesadas."
    )


if __name__ == "__main__":
    main()
