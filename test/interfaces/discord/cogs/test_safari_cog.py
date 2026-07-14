from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from application.safari import (
    OpenSafariRegistrationResult,
    SafariActivityAlreadyExists,
    SafariUnlockUnavailable,
    StartSafariResult,
)
from core.safari import SafariGeneratedEncounter, SafariThematicEvent
from core.safari.domain import SAFARI_LEVEL_CONFIGS, SafariMapInfluence
from core.safari.registration import SafariRegistration
from core.safari.unlock import SafariUnlock
from interfaces.discord.cogs.safari_cog import SafariCog
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from interfaces.discord.views.safari_registration_view import SafariRegistrationView
from test.unit.safari.test_session import make_encounter, make_session


def _registration_result() -> OpenSafariRegistrationResult:
    registration = SafariRegistration(
        guild_id=10,
        unlock_id=1,
        participant_ids=(20,),
        opened_at=datetime(2026, 7, 13, tzinfo=UTC),
    )
    unlock = SafariUnlock(
        id=1,
        guild_id=10,
        level=4,
        encounter_count=6,
        balls_per_participant=3,
        unlocked_at=datetime(2026, 7, 13, tzinfo=UTC),
        map_influence=SafariMapInfluence(),
    )
    return OpenSafariRegistrationResult(
        registration=registration,
        unlock=unlock,
        level=unlock.level,
        encounter_count=unlock.encounter_count,
        balls_per_participant=unlock.balls_per_participant,
        capacity=10,
    )


def _start_result() -> StartSafariResult:
    session = make_session()
    encounter = make_encounter((25,))
    session.publish_encounter(encounter)
    return StartSafariResult(
        session=session,
        unlock=_registration_result().unlock,
        generated_encounter=SafariGeneratedEncounter(
            encounter=encounter,
            event=SafariThematicEvent.NONE,
        ),
    )


@pytest.mark.asyncio
async def test_safari_command_opens_registration_view() -> None:
    open_registration = AsyncMock(return_value=_registration_result())
    core = SimpleNamespace(
        safari_registration_application=SimpleNamespace(open=open_registration),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        author=SimpleNamespace(id=20),
        send=AsyncMock(),
    )

    await SafariCog.safari.callback(cog, ctx)

    open_registration.assert_awaited_once()
    kwargs = ctx.send.await_args.kwargs
    assert isinstance(kwargs["view"], SafariRegistrationView)
    assert kwargs["embed"].title.endswith("Safari Registration")


@pytest.mark.asyncio
async def test_safari_command_rejects_dm_context() -> None:
    core = SimpleNamespace(
        safari_registration_application=SimpleNamespace(open=AsyncMock()),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(guild=None, author=SimpleNamespace(id=20), send=AsyncMock())

    await SafariCog.safari.callback(cog, ctx)

    ctx.send.assert_awaited_once_with("Safari can only be used in a server.")


@pytest.mark.asyncio
async def test_safari_command_reports_registration_errors() -> None:
    open_registration = AsyncMock(side_effect=SafariUnlockUnavailable())
    core = SimpleNamespace(
        safari_registration_application=SimpleNamespace(open=open_registration),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        author=SimpleNamespace(id=20),
        send=AsyncMock(),
    )

    await SafariCog.safari.callback(cog, ctx)

    ctx.send.assert_awaited_once_with("No Safari unlock is available for this guild.")


@pytest.mark.asyncio
async def test_safari_command_reports_existing_activity() -> None:
    open_registration = AsyncMock(side_effect=SafariActivityAlreadyExists())
    core = SimpleNamespace(
        safari_registration_application=SimpleNamespace(open=open_registration),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        author=SimpleNamespace(id=20),
        send=AsyncMock(),
    )

    await SafariCog.safari.callback(cog, ctx)

    ctx.send.assert_awaited_once_with(
        "A Safari activity is already active for this guild."
    )


@pytest.mark.asyncio
async def test_safariunlock_creates_unlock_with_real_level_configuration() -> None:
    saved_unlock = None

    async def _save(unlock):
        nonlocal saved_unlock
        saved_unlock = unlock
        unlock.id = 7
        return unlock

    core = SimpleNamespace(
        safari_unlock_repository=SimpleNamespace(save=AsyncMock(side_effect=_save)),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10, owner_id=20),
        author=SimpleNamespace(
            id=20, guild_permissions=SimpleNamespace(administrator=True)
        ),
        send=AsyncMock(),
    )

    await SafariCog.safariunlock.callback(cog, ctx, 3)

    core.safari_unlock_repository.save.assert_awaited_once()
    assert saved_unlock is not None
    assert saved_unlock.guild_id == 10
    assert saved_unlock.level == 3
    assert saved_unlock.encounter_count == SAFARI_LEVEL_CONFIGS[3].encounter_count
    assert (
        saved_unlock.balls_per_participant
        == SAFARI_LEVEL_CONFIGS[3].balls_per_participant
    )
    kwargs = ctx.send.await_args.args[0]
    assert "Safari level 3 unlocked for this server." in kwargs
    assert f"Decisions: {SAFARI_LEVEL_CONFIGS[3].decision_count}" in kwargs


@pytest.mark.asyncio
async def test_safariunlock_defaults_to_level_one() -> None:
    saved_unlock = None

    async def _save(unlock):
        nonlocal saved_unlock
        saved_unlock = unlock
        unlock.id = 1
        return unlock

    core = SimpleNamespace(
        safari_unlock_repository=SimpleNamespace(save=AsyncMock(side_effect=_save)),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10, owner_id=20),
        author=SimpleNamespace(
            id=20, guild_permissions=SimpleNamespace(administrator=False)
        ),
        send=AsyncMock(),
    )

    await SafariCog.safariunlock.callback(cog, ctx)

    assert saved_unlock is not None
    assert saved_unlock.level == 1
    assert saved_unlock.encounter_count == SAFARI_LEVEL_CONFIGS[1].encounter_count


@pytest.mark.asyncio
async def test_safariunlock_rejects_invalid_level() -> None:
    core = SimpleNamespace(
        safari_unlock_repository=SimpleNamespace(save=AsyncMock()),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10, owner_id=20),
        author=SimpleNamespace(
            id=20, guild_permissions=SimpleNamespace(administrator=True)
        ),
        send=AsyncMock(),
    )

    await SafariCog.safariunlock.callback(cog, ctx, 99)

    ctx.send.assert_awaited_once()
    assert "Invalid Safari level." in ctx.send.await_args.args[0]
    assert "Available levels" in ctx.send.await_args.args[0]
    core.safari_unlock_repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_safariunlock_rejects_non_admin_users() -> None:
    core = SimpleNamespace(
        safari_unlock_repository=SimpleNamespace(save=AsyncMock()),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10, owner_id=999),
        author=SimpleNamespace(
            id=20, guild_permissions=SimpleNamespace(administrator=False)
        ),
        send=AsyncMock(),
    )

    await SafariCog.safariunlock.callback(cog, ctx, 1)

    ctx.send.assert_awaited_once_with(
        "You must be the server owner or have administrator permissions."
    )
    core.safari_unlock_repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_safariunlock_rejects_dm_context() -> None:
    core = SimpleNamespace(
        safari_unlock_repository=SimpleNamespace(save=AsyncMock()),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=None,
        author=SimpleNamespace(
            id=20, guild_permissions=SimpleNamespace(administrator=True)
        ),
        send=AsyncMock(),
    )

    await SafariCog.safariunlock.callback(cog, ctx, 1)

    ctx.send.assert_awaited_once_with("Safari can only be used in a server.")
    core.safari_unlock_repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_safaritest_opens_solo_registration_and_shows_first_encounter() -> None:
    open_registration = AsyncMock(return_value=_registration_result())
    start_test = AsyncMock(return_value=_start_result())
    core = SimpleNamespace(
        safari_registration_application=SimpleNamespace(
            open=open_registration,
            join=AsyncMock(),
        ),
        start_safari_application=SimpleNamespace(start_for_testing=start_test),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10, owner_id=20),
        author=SimpleNamespace(
            id=20, guild_permissions=SimpleNamespace(administrator=True)
        ),
        send=AsyncMock(),
    )

    await SafariCog.safaritest.callback(cog, ctx)

    open_registration.assert_awaited_once()
    start_test.assert_awaited_once_with(10, ANY)
    kwargs = ctx.send.await_args.kwargs
    assert isinstance(kwargs["view"], SafariEncounterView)


@pytest.mark.asyncio
async def test_safaritest_joins_existing_registration_idempotently() -> None:
    open_registration = AsyncMock(side_effect=SafariActivityAlreadyExists())
    join_registration = AsyncMock(return_value=_registration_result())
    start_test = AsyncMock(return_value=_start_result())
    core = SimpleNamespace(
        safari_registration_application=SimpleNamespace(
            open=open_registration,
            join=join_registration,
        ),
        start_safari_application=SimpleNamespace(start_for_testing=start_test),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10, owner_id=20),
        author=SimpleNamespace(
            id=20, guild_permissions=SimpleNamespace(administrator=True)
        ),
        send=AsyncMock(),
    )

    await SafariCog.safaritest.callback(cog, ctx)

    join_registration.assert_awaited_once_with(10, 20)
    start_test.assert_awaited_once()


@pytest.mark.asyncio
async def test_safaritest_rejects_non_admin_users_and_dm_context() -> None:
    core = SimpleNamespace(
        safari_registration_application=SimpleNamespace(
            open=AsyncMock(), join=AsyncMock()
        ),
        start_safari_application=SimpleNamespace(start_for_testing=AsyncMock()),
    )
    cog = SafariCog(core)
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=10, owner_id=999),
        author=SimpleNamespace(
            id=20, guild_permissions=SimpleNamespace(administrator=False)
        ),
        send=AsyncMock(),
    )

    await SafariCog.safaritest.callback(cog, ctx)

    ctx.send.assert_awaited_once_with(
        "You must be the server owner or have administrator permissions."
    )

    dm_ctx = SimpleNamespace(
        guild=None, author=SimpleNamespace(id=20), send=AsyncMock()
    )
    await SafariCog.safaritest.callback(cog, dm_ctx)
    dm_ctx.send.assert_awaited_once_with("Safari can only be used in a server.")
