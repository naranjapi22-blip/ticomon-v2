from dotenv import load_dotenv
import os
from pathlib import Path
import psycopg2

# 🔥 SIEMPRE cargar .env aquí (infra layer)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


def get_connection():
    db_url = os.getenv("NEON_DATABASE_URL")

    if not db_url:
        raise Exception("❌ NEON_DATABASE_URL no encontrada")

    return psycopg2.connect(db_url)