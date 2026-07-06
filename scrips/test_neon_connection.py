import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# 🔥 cargar .env desde raíz
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


def get_connection():
    db_url = os.getenv("NEON_DATABASE_URL")

    if not db_url:
        raise Exception("❌ NEON_DATABASE_URL no está definida en .env")

    return psycopg2.connect(db_url)


def main():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT 1;")
    print("✔ Conexión:", cur.fetchone())

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
