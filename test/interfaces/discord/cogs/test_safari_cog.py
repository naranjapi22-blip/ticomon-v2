from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.safari import (
    OpenSafariRegistrationResult,
    SafariActivityAlreadyExists,
    SafariUnlockUnavailable,
)
from core.safari.domain import SafariMapInfluence
from core.safari.registration import SafariRegistration
from core.safari.unlock import SafariUnlock
from interfaces.discord.cogs.safari_cog import SafariCog
from interfaces.discord.views.safari_registration_view import SafariRegistrationView


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
