import asyncio

from infrastructure.db_config import close_pool, get_pool


async def create_mint_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute("""
                ALTER TABLE creatures
                ADD COLUMN IF NOT EXISTS minted_nature VARCHAR(20) NULL
                """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS trainer_mints (
                    trainer_id BIGINT PRIMARY KEY REFERENCES trainers(trainer_id),
                    amount INTEGER NOT NULL CHECK (amount >= 0)
                )
                """)
    await close_pool()


async def main() -> None:
    await create_mint_schema()


if __name__ == "__main__":
    asyncio.run(main())
