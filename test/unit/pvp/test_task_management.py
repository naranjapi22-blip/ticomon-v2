from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest

from application.pvp.pvp_application_service import PvpApplicationService
from application.pvp.task_management import (
    cancel_task_safely,
    cancel_tasks_safely,
    unique_pending_tasks,
)
from core.pvp.session import PvpPhase, PvpSessionRegistry


@pytest.mark.asyncio
async def test_cancel_task_safely_skips_the_current_task(caplog):
    caplog.set_level(logging.WARNING)
    current = asyncio.current_task()

    assert current is not None
    assert not await cancel_task_safely(
        current,
        current_task=current,
        owner="test",
        reason="self-cancel regression",
    )
    assert not current.cancelled()
    assert "Skipping self-cancellation" in caplog.text


@pytest.mark.asyncio
async def test_cancel_tasks_safely_deduplicates_and_ignores_completed_tasks():
    event = asyncio.Event()
    pending = asyncio.create_task(event.wait(), name="pvp-duplicate-task")
    completed = asyncio.create_task(asyncio.sleep(0), name="pvp-completed-task")
    await completed

    await cancel_tasks_safely(
        (pending, pending, completed),
        owner="test",
        reason="duplicate-task regression",
    )

    assert pending.cancelled()
    assert completed.done()


def test_task_management_does_not_require_private_task_attributes():
    class TaskLikeWithoutInternals:
        def done(self):
            return False

    assert unique_pending_tasks((TaskLikeWithoutInternals(),)) == ()


@pytest.mark.asyncio
async def test_cancel_tasks_safely_ignores_futures_not_tasks():
    future = asyncio.get_running_loop().create_future()

    await cancel_tasks_safely(
        (future,),
        owner="test",
        reason="future regression",
    )

    assert not future.cancelled()


@pytest.mark.asyncio
async def test_cleanup_called_from_delivery_task_does_not_cancel_itself():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    delivery_task = asyncio.current_task()
    session.timeout_tasks.add(delivery_task)

    await service.cleanup(session.id)

    assert session.phase is PvpPhase.CLEANED_UP
    assert service.is_cleaned_up(session.id)


@pytest.mark.asyncio
async def test_two_simultaneous_cleanups_close_controller_once():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    release = asyncio.Event()
    close_calls = []

    async def close():
        close_calls.append("close")
        await release.wait()

    session.battle_controller = SimpleNamespace(close=close)
    first = asyncio.create_task(service.cleanup(session.id), name="pvp-cleanup-1")
    await asyncio.sleep(0)
    second = asyncio.create_task(service.cleanup(session.id), name="pvp-cleanup-2")
    await asyncio.sleep(0)
    release.set()
    await asyncio.gather(first, second)

    assert close_calls == ["close"]
    assert session.phase is PvpPhase.CLEANED_UP


@pytest.mark.asyncio
async def test_concurrent_cleanup_stress_has_no_recursion_or_pending_tasks():
    created_tasks = []
    for _ in range(100):
        service = PvpApplicationService(registry=PvpSessionRegistry())
        session = service.challenge(1, 2)
        close_started = asyncio.Event()

        async def close():
            close_started.set()
            await asyncio.sleep(0)

        session.battle_controller = SimpleNamespace(close=close)
        first = asyncio.create_task(service.cleanup(session.id), name="pvp-stress-1")
        second = asyncio.create_task(service.cleanup(session.id), name="pvp-stress-2")
        created_tasks.extend((first, second))
        await asyncio.gather(first, second)
        assert close_started.is_set()
        assert session.phase is PvpPhase.CLEANED_UP

    await asyncio.sleep(0)
    assert all(task.done() for task in created_tasks)


@pytest.mark.asyncio
async def test_controller_close_called_from_its_callback_does_not_await_callback():
    from infrastructure.battle.poke_env.pvp_controller import PokeEnvPvpController

    controller = PokeEnvPvpController()
    player = SimpleNamespace(
        _closing=False,
        ps_client=SimpleNamespace(
            stop_listening=lambda: asyncio.sleep(0),
            _active_tasks=set(),
        ),
    )
    controller._players = (player,)

    callback_task = asyncio.create_task(controller.close(), name="pvp-final-callback")
    controller._callback_tasks.add(callback_task)
    await callback_task

    assert controller._players is None
    assert not controller._callback_tasks


@pytest.mark.asyncio
async def test_controller_close_does_not_wait_for_current_battle_task():
    from infrastructure.battle.poke_env.pvp_controller import PokeEnvPvpController

    controller = PokeEnvPvpController()
    controller._battle_task = asyncio.current_task()

    await controller.close()

    assert controller._battle_task is None


@pytest.mark.asyncio
async def test_controller_close_deduplicates_shared_player_tasks(monkeypatch):
    import infrastructure.battle.poke_env.pvp_controller as controller_module
    from infrastructure.battle.poke_env.pvp_controller import PokeEnvPvpController

    monkeypatch.setattr(
        controller_module, "SHOWDOWN_MESSAGE_CLOSE_TIMEOUT_SECONDS", 0.01
    )
    task = asyncio.create_task(asyncio.Event().wait(), name="pvp-shared-listener")
    players = tuple(
        SimpleNamespace(
            _closing=True,
            ps_client=SimpleNamespace(
                stop_listening=lambda: asyncio.sleep(0),
                _active_tasks={task},
            ),
        )
        for _ in range(2)
    )
    controller = PokeEnvPvpController()
    controller._players = players

    await controller.close()

    assert task.cancelled()


@pytest.mark.asyncio
async def test_cancel_task_safely_does_not_hide_unexpected_task_errors():
    async def fail_during_cancel():
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError as error:
            raise RuntimeError("unexpected shutdown failure") from error

    task = asyncio.create_task(fail_during_cancel(), name="pvp-failing-task")
    await asyncio.sleep(0)
    with pytest.raises(RuntimeError, match="unexpected shutdown failure"):
        await cancel_task_safely(
            task,
            owner="test",
            reason="unexpected-error regression",
        )
