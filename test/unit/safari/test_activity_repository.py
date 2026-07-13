import asyncio
from datetime import datetime

import pytest

from core.safari import SafariRegistration
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
from test.unit.safari.test_session import make_session


def make_registration(guild_id: int, trainer_id: int) -> SafariRegistration:
    return SafariRegistration(
        guild_id=guild_id,
        unlock_id=1,
        participant_ids={trainer_id},
        opened_at=datetime(2026, 7, 12, 10, 0),
    )


@pytest.mark.asyncio
async def test_repository_starts_empty_and_saves_registration():
    repository = InMemorySafariActivityRepository()
    registration = make_registration(1, 10)

    assert await repository.get_registration(1) is None

    await repository.save_registration(registration)

    assert await repository.get_registration(1) is registration


@pytest.mark.asyncio
async def test_repository_replaces_registration_for_same_guild():
    repository = InMemorySafariActivityRepository()
    first = make_registration(1, 10)
    replacement = make_registration(1, 20)

    await repository.save_registration(first)
    await repository.save_registration(replacement)

    assert await repository.get_registration(1) is replacement


@pytest.mark.asyncio
async def test_repository_keeps_guild_registrations_separate():
    repository = InMemorySafariActivityRepository()
    first = make_registration(1, 10)
    second = make_registration(2, 20)

    await repository.save_registration(first)
    await repository.save_registration(second)

    assert await repository.get_registration(1) is first
    assert await repository.get_registration(2) is second


@pytest.mark.asyncio
async def test_clear_registration_is_idempotent():
    repository = InMemorySafariActivityRepository()
    await repository.save_registration(make_registration(1, 10))

    await repository.clear_registration(1)
    await repository.clear_registration(1)

    assert await repository.get_registration(1) is None


@pytest.mark.asyncio
async def test_new_repository_instance_starts_empty():
    repository = InMemorySafariActivityRepository()
    await repository.save_registration(make_registration(1, 10))

    new_repository = InMemorySafariActivityRepository()

    assert await new_repository.get_registration(1) is None


@pytest.mark.asyncio
async def test_session_replaces_registration_as_the_single_guild_activity():
    repository = InMemorySafariActivityRepository()
    registration = make_registration(10, 100)
    session = make_session()

    await repository.save_registration(registration)
    await repository.save_session(session)

    assert await repository.get_registration(10) is None
    assert await repository.get_session(10) is session
    assert await repository.get_activity(10) is session


@pytest.mark.asyncio
async def test_registration_cannot_replace_an_active_session():
    repository = InMemorySafariActivityRepository()
    await repository.save_session(make_session())

    with pytest.raises(ValueError):
        await repository.save_registration(make_registration(10, 100))


@pytest.mark.asyncio
async def test_clear_session_is_idempotent():
    repository = InMemorySafariActivityRepository()
    await repository.save_session(make_session())

    await repository.clear_session(10)
    await repository.clear_session(10)

    assert await repository.get_activity(10) is None


@pytest.mark.asyncio
async def test_same_guild_lock_serializes_access():
    repository = InMemorySafariActivityRepository()
    lock = repository.lock(1)
    attempting = asyncio.Event()
    entered = asyncio.Event()

    async def enter_same_guild_lock() -> None:
        attempting.set()
        async with repository.lock(1):
            entered.set()

    await lock.acquire()
    task = asyncio.create_task(enter_same_guild_lock())
    await attempting.wait()

    assert repository.lock(1) is lock
    assert not entered.is_set()

    lock.release()
    await task

    assert entered.is_set()


@pytest.mark.asyncio
async def test_different_guild_locks_are_independent():
    repository = InMemorySafariActivityRepository()
    first_lock = repository.lock(1)
    second_lock = repository.lock(2)
    entered = asyncio.Event()

    async def enter_second_guild_lock() -> None:
        async with second_lock:
            entered.set()

    await first_lock.acquire()
    task = asyncio.create_task(enter_second_guild_lock())
    await entered.wait()

    assert first_lock is not second_lock
    assert entered.is_set()

    first_lock.release()
    await task
