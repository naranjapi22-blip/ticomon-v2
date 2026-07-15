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
