from types import SimpleNamespace

import pytest
from asyncpg.exceptions import UndefinedTableError

from infrastructure.persistence.repositories.neon_shop_repository import (
    NeonShopRepository,
)


@pytest.mark.asyncio
async def test_missing_shop_schema_has_explicit_error_and_single_traceback(
    monkeypatch, caplog
):
    repository = NeonShopRepository.__new__(NeonShopRepository)
    error = UndefinedTableError('relation "shop_purchase_receipts" does not exist')

    async def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(repository, "_purchase", fail)
    creature = SimpleNamespace(
        species=SimpleNamespace(name="alcremie", id=869),
        current_form=SimpleNamespace(id=80, name="salted-cream-love"),
    )

    with pytest.raises(ValueError, match="Shop schema is not initialized"):
        await repository.purchase(
            7, creature, SimpleNamespace(items=lambda: ()), "alcremie:80", "key"
        )
    records = [
        record for record in caplog.records if "shop_purchase_failed" in record.message
    ]
    assert len(records) == 1
    assert records[0].exc_info is not None
