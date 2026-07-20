from __future__ import annotations

import os
from pathlib import Path

import pytest
import pytest_asyncio


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    neon_database_url = os.getenv("NEON_DATABASE_URL")
    skip_neon_db = pytest.mark.skip(reason="NEON_DATABASE_URL is not set.")

    for item in items:
        path = Path(str(item.path))
        if "integration" in path.parts or path.name.startswith("test_neon_"):
            item.add_marker("neon_db")
            if not neon_database_url:
                item.add_marker(skip_neon_db)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_neon_creature_loadout_schema():
    """Prepare loadout columns before any Neon test can write creatures."""
    if os.getenv("NEON_DATABASE_URL"):
        from infrastructure.db_config import close_pool
        from scripts.create_creature_loadout_schema import (
            create_creature_loadout_schema,
        )

        await create_creature_loadout_schema()
        yield
        await close_pool()
        return
    yield
