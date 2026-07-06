import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# 🔥 cargar .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


def get_connection():
    db_url = os.getenv("NEON_DATABASE_URL")

    if not db_url:
        raise Exception("❌ NEON_DATABASE_URL no encontrada")

    return psycopg2.connect(db_url)


def insert_bulbasaur(conn):
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO species (
            pokeapi_id, name,
            type_1, type_2,
            height, weight, display_scale,
            capture_rate, is_legendary, is_mythical,
            hp, attack, defense,
            special_attack, special_defense, speed
        )
        VALUES (
            1, 'bulbasaur',
            'grass', 'poison',
            7, 69, 1.0,
            45, false, false,
            45, 49, 49,
            65, 65, 45
        )
        ON CONFLICT (pokeapi_id) DO NOTHING;
    """
    )

    conn.commit()
    cur.close()


def main():
    conn = get_connection()

    insert_bulbasaur(conn)

    conn.close()

    print("✔ Bulbasaur insertado en Neon DB")


if __name__ == "__main__":
    main()
