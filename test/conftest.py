from __future__ import annotations

import os
from pathlib import Path

import pytest


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
