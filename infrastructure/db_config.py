import asyncio
import logging
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

_pool: asyncpg.Pool | None = None
_pool_loop: asyncio.AbstractEventLoop | None = None
logger = logging.getLogger(__name__)


async def get_pool() -> asyncpg.Pool:
    """
    Returns the shared PostgreSQL connection pool.
    """

    global _pool, _pool_loop

    current_loop = asyncio.get_running_loop()

    if _pool is not None:
        pool_loop = getattr(_pool, "_loop", None)
        if not isinstance(pool_loop, asyncio.AbstractEventLoop):
            pool_loop = _pool_loop
        is_closed = False
        is_closing = getattr(_pool, "is_closing", None)
        if callable(is_closing) and not asyncio.iscoroutinefunction(is_closing):
            closing_result = is_closing()
            is_closed = isinstance(closing_result, bool) and closing_result
        if is_closed or (pool_loop is not None and pool_loop is not current_loop):
            if pool_loop is current_loop:
                await _pool.close()
            elif not (
                isinstance(pool_loop, asyncio.AbstractEventLoop)
                and pool_loop.is_closed()
            ):
                terminate = getattr(_pool, "terminate", None)
                if callable(terminate):
                    termination = terminate()
                    if asyncio.iscoroutine(termination):
                        await termination
            _pool = None
            _pool_loop = None

    if _pool is None:

        database_url = os.getenv("NEON_DATABASE_URL")

        if database_url is None:
            raise RuntimeError("NEON_DATABASE_URL not found.")

        _pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=10,
            statement_cache_size=0,
        )
        _pool_loop = current_loop
        logger.debug("PostgreSQL pool created")

    return _pool


async def close_pool() -> None:
    """
    Closes the shared connection pool.
    """

    global _pool, _pool_loop

    if _pool is not None:
        pool_loop = getattr(_pool, "_loop", None)
        if not isinstance(pool_loop, asyncio.AbstractEventLoop):
            pool_loop = _pool_loop
        current_loop = asyncio.get_running_loop()
        if pool_loop is current_loop:
            await _pool.close()
        elif not (
            isinstance(pool_loop, asyncio.AbstractEventLoop) and pool_loop.is_closed()
        ):
            terminate = getattr(_pool, "terminate", None)
            if callable(terminate):
                termination = terminate()
                if asyncio.iscoroutine(termination):
                    await termination
        _pool = None
        _pool_loop = None
        logger.debug("PostgreSQL pool closed")
