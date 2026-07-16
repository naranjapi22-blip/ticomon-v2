import asyncio

from infrastructure.db_config import close_pool, get_pool
from scripts.creature_schema import (
    ensure_creature_minted_nature,
    ensure_creature_original_trainer_id,
)


async def create_trade_schema() -> None:
    """Creates the PostgreSQL structures required by the Trade module."""

    pool = await get_pool()

    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id BIGSERIAL PRIMARY KEY,
                    initiator_trainer_id BIGINT NOT NULL,
                    counterparty_trainer_id BIGINT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    initiator_accepted_at TIMESTAMPTZ NULL,
                    counterparty_accepted_at TIMESTAMPTZ NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ NULL,
                    completed_at TIMESTAMPTZ NULL,
                    cancelled_by_trainer_id BIGINT NULL,
                    rejected_by_trainer_id BIGINT NULL,
                    CONSTRAINT trades_distinct_participants
                        CHECK (initiator_trainer_id <> counterparty_trainer_id),
                    CONSTRAINT trades_valid_status
                        CHECK (status IN (
                            'draft',
                            'open',
                            'completed',
                            'cancelled',
                            'rejected',
                            'expired'
                        ))
                )
                """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS trade_offer_items (
                    trade_id BIGINT NOT NULL
                        REFERENCES trades(id) ON DELETE CASCADE,
                    offering_trainer_id BIGINT NOT NULL,
                    creature_id BIGINT NOT NULL,
                    collection_number_at_offer INTEGER NOT NULL,
                    PRIMARY KEY (trade_id, creature_id)
                )
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS trades_initiator_status_idx
                ON trades (initiator_trainer_id, status)
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS trades_counterparty_status_idx
                ON trades (counterparty_trainer_id, status)
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS trades_completed_at_idx
                ON trades (completed_at)
                """)
            for column in (
                "initiator_accepted_at",
                "counterparty_accepted_at",
                "created_at",
                "expires_at",
                "completed_at",
            ):
                await connection.execute(f"""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = 'trades'
                              AND column_name = '{column}'
                              AND data_type = 'timestamp without time zone'
                        ) THEN
                            EXECUTE '
                                ALTER TABLE trades
                                ALTER COLUMN {column}
                                TYPE TIMESTAMPTZ
                                USING {column} AT TIME ZONE ''UTC''
                            ';
                        END IF;
                    END
                    $$;
                    """)
            await connection.execute("""
                ALTER TABLE creatures
                DROP CONSTRAINT IF EXISTS uq_trainer_collection
                """)
            await ensure_creature_original_trainer_id(connection)
            await ensure_creature_minted_nature(connection)
            await connection.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'creatures_trainer_collection_number_unique'
                    ) THEN
                        ALTER TABLE creatures
                        ADD CONSTRAINT
                            creatures_trainer_collection_number_unique
                        UNIQUE (trainer_id, collection_number)
                        DEFERRABLE INITIALLY IMMEDIATE;
                    END IF;
                END
                $$
                """)

    await close_pool()


async def main() -> None:
    await create_trade_schema()
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
