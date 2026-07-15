import asyncio
import json
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio

from application.achievement.contracts import (
    AchievementActivity,
    AchievementActivityType,
)
from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from infrastructure.db_config import close_pool, get_pool
from infrastructure.persistence.repositories import (
    neon_achievement_activity_repository,
    neon_achievement_unlock_repository,
)
from scripts.create_achievement_schema import create_achievement_schema

ActivityRepository = (
    neon_achievement_activity_repository.NeonAchievementActivityRepository
)
UnlockRepository = neon_achievement_unlock_repository.NeonAchievementUnlockRepository

NOW = datetime(2026, 7, 15, tzinfo=UTC)


@pytest_asyncio.fixture
async def achievement_trainer_factory():
    await close_pool()
    await create_achievement_schema()
    pool = await get_pool()
    trainer_ids: list[int] = []
    creature_ids: list[int] = []

    async def create() -> tuple[int, int]:
        trainer_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
        async with pool.acquire() as connection:
            creature_id = await connection.fetchval(
                """
                INSERT INTO creatures (
                    trainer_id, original_trainer_id, collection_number,
                    species_id, current_form_id, is_shiny, nature, size,
                    hp_iv, attack_iv, defense_iv, special_attack_iv,
                    special_defense_iv, speed_iv
                )
                VALUES (
                    $1, $1, 1, 1, NULL, FALSE, 'hardy', 1.0,
                    31, 31, 31, 31, 31, 31
                )
                RETURNING id
                """,
                trainer_id,
            )
            await connection.execute(
                """
                INSERT INTO trainers (trainer_id, starter_creature_id, started_at)
                VALUES ($1, $2, NOW())
                """,
                trainer_id,
                creature_id,
            )
        trainer_ids.append(trainer_id)
        creature_ids.append(creature_id)
        return trainer_id, creature_id

    yield create

    async with pool.acquire() as connection:
        if trainer_ids:
            await connection.execute(
                "DELETE FROM trainer_achievement_activities WHERE trainer_id = ANY($1)",
                trainer_ids,
            )
            await connection.execute(
                "DELETE FROM trainer_achievement_unlocks WHERE trainer_id = ANY($1)",
                trainer_ids,
            )
            await connection.execute(
                "DELETE FROM trainer_candies WHERE trainer_id = ANY($1)",
                trainer_ids,
            )
            await connection.execute(
                "DELETE FROM trainers WHERE trainer_id = ANY($1)",
                trainer_ids,
            )
        if creature_ids:
            await connection.execute(
                "DELETE FROM creatures WHERE id = ANY($1)",
                creature_ids,
            )
    await close_pool()


@pytest.mark.asyncio
async def test_activity_recording_is_idempotent_per_trainer(
    achievement_trainer_factory,
):
    trainer_id, _ = await achievement_trainer_factory()
    repository = ActivityRepository()
    activity = AchievementActivity(
        trainer_id=trainer_id,
        activity_type=AchievementActivityType.CAPTURE,
        species_id=1,
        idempotency_key="creature:1",
        occurred_at=NOW,
    )

    assert await repository.record(activity) is True
    assert await repository.record(activity) is False
    assert (await repository.get_progress(trainer_id)).capture_count == 1


@pytest.mark.asyncio
async def test_same_activity_key_is_allowed_for_different_trainers(
    achievement_trainer_factory,
):
    first_trainer_id, _ = await achievement_trainer_factory()
    second_trainer_id, _ = await achievement_trainer_factory()
    repository = ActivityRepository()

    results = await asyncio.gather(
        repository.record(
            AchievementActivity(
                trainer_id=first_trainer_id,
                activity_type=AchievementActivityType.CAPTURE,
                species_id=1,
                idempotency_key="creature:1",
            )
        ),
        repository.record(
            AchievementActivity(
                trainer_id=second_trainer_id,
                activity_type=AchievementActivityType.CAPTURE,
                species_id=1,
                idempotency_key="creature:1",
            )
        ),
    )

    assert results == [True, True]


@pytest.mark.asyncio
async def test_concurrent_discovery_of_one_species_creates_one_fact(
    achievement_trainer_factory,
):
    trainer_id, _ = await achievement_trainer_factory()
    repository = ActivityRepository()

    results = await asyncio.gather(
        *(
            repository.record(
                AchievementActivity(
                    trainer_id=trainer_id,
                    activity_type=AchievementActivityType.SPECIES_DISCOVERED,
                    species_id=1,
                    idempotency_key=f"creature:{number}",
                )
            )
            for number in (1, 2)
        )
    )

    assert sorted(results) == [False, True]
    assert (await repository.get_progress(trainer_id)).unique_discovered_species == 1


@pytest.mark.asyncio
async def test_progress_counts_capture_species_and_shiny_activities(
    achievement_trainer_factory,
):
    trainer_id, _ = await achievement_trainer_factory()
    repository = ActivityRepository()
    activities = (
        (AchievementActivityType.CAPTURE, 1, "capture:1"),
        (AchievementActivityType.CAPTURE, 2, "capture:2"),
        (AchievementActivityType.SHINY_CAPTURE, 2, "capture:2"),
        (AchievementActivityType.SPECIES_DISCOVERED, 1, "capture:1"),
        (AchievementActivityType.SPECIES_DISCOVERED, 2, "capture:2"),
    )
    for activity_type, species_id, key in activities:
        assert await repository.record(
            AchievementActivity(
                trainer_id=trainer_id,
                activity_type=activity_type,
                species_id=species_id,
                idempotency_key=key,
            )
        )

    progress = await repository.get_progress(trainer_id)
    assert progress.capture_count == 2
    assert progress.shiny_capture_count == 1
    assert progress.unique_discovered_species == 2


@pytest.mark.asyncio
async def test_unlock_award_is_concurrent_idempotent_and_auditable(
    achievement_trainer_factory,
):
    trainer_id, _ = await achievement_trainer_factory()
    repository = UnlockRepository()
    reward = CandyBundle.from_amounts(
        CandyAmount(CandyType.GRASS, 2),
        CandyAmount(CandyType.POISON, 2),
    )

    results = await asyncio.gather(
        repository.award(trainer_id, "first_capture", reward, NOW),
        repository.award(trainer_id, "first_capture", reward, NOW),
    )

    assert sorted(results) == [False, True]
    unlocks = await repository.get_by_trainer(trainer_id)
    assert unlocks[0].rewarded_candies == reward

    pool = await get_pool()
    async with pool.acquire() as connection:
        persisted = await connection.fetchval(
            """
            SELECT rewarded_candies
            FROM trainer_achievement_unlocks
            WHERE trainer_id = $1 AND achievement_id = 'first_capture'
            """,
            trainer_id,
        )
        candies = await connection.fetch(
            """
            SELECT candy_type, amount
            FROM trainer_candies
            WHERE trainer_id = $1
            ORDER BY candy_type
            """,
            trainer_id,
        )

    if isinstance(persisted, str):
        persisted = json.loads(persisted)
    assert persisted == {"grass": 2, "poison": 2}
    assert [(row["candy_type"], row["amount"]) for row in candies] == [
        ("grass", 2),
        ("poison", 2),
    ]
