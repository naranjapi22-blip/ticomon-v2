import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """
    Returns the shared PostgreSQL connection pool.
    """

    global _pool

    if _pool is None:

        database_url = os.getenv("NEON_DATABASE_URL")

        if database_url is None:
            raise RuntimeError("NEON_DATABASE_URL not found.")

        _pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=10,
        )

    return _pool


async def close_pool() -> None:
    """
    Closes the shared connection pool.
    """

    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None
