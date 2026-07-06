import pytest_asyncio

from infrastructure.db_config import close_pool


@pytest_asyncio.fixture(autouse=True)
async def cleanup_pool():
    yield

    await close_pool()
