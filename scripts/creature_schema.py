from __future__ import annotations


async def ensure_creature_original_trainer_id(connection) -> None:
    await connection.execute("""
        ALTER TABLE creatures
        ADD COLUMN IF NOT EXISTS original_trainer_id BIGINT
        """)
    await connection.execute("""
        UPDATE creatures
        SET original_trainer_id = trainer_id
        WHERE original_trainer_id IS NULL
        """)
    await connection.execute("""
        ALTER TABLE creatures
        ALTER COLUMN original_trainer_id SET NOT NULL
        """)


async def ensure_creature_minted_nature(connection) -> None:
    await connection.execute("""
        ALTER TABLE creatures
        ADD COLUMN IF NOT EXISTS minted_nature VARCHAR(20) NULL
        """)


async def ensure_creature_loadout_columns(connection) -> None:
    """Ensures creature loadout columns exist for every database setup path."""
    await connection.execute("""
        ALTER TABLE creatures
        ADD COLUMN IF NOT EXISTS ability_id TEXT NULL
        """)
    await connection.execute("""
        ALTER TABLE creatures
        ADD COLUMN IF NOT EXISTS equipped_moves TEXT[] NOT NULL DEFAULT '{}'
        """)
    await connection.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'creatures_equipped_moves_max_four'
            ) THEN
                ALTER TABLE creatures
                ADD CONSTRAINT creatures_equipped_moves_max_four
                CHECK (cardinality(equipped_moves) <= 4);
            END IF;
        END
        $$
        """)
