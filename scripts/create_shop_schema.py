import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infrastructure.db_config import close_pool, get_pool


async def create_shop_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS shop_purchase_receipts (
                    idempotency_key VARCHAR(160) PRIMARY KEY,
                    trainer_id BIGINT NOT NULL REFERENCES trainers(trainer_id),
                    product_id VARCHAR(80) NOT NULL,
                    creature_id BIGINT NOT NULL REFERENCES creatures(id),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS shop_purchase_receipts_trainer_idx
                ON shop_purchase_receipts (trainer_id, created_at)
                """)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(create_shop_schema())
