from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.safari import (
    OpenSafariRegistrationResult,
    StartSafariResult,
)
from core.safari import SafariGeneratedEncounter, SafariThematicEvent
from core.safari.domain import SafariMapInfluence
from core.safari.registration import SafariRegistration
from core.safari.unlock import SafariUnlock
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from interfaces.discord.views.safari_registration_view import SafariRegistrationView
from test.unit.safari.test_session import make_encounter, make_session


def _registration_result() -> OpenSafariRegistrationResult:
    registration = SafariRegistration(
        guild_id=10,
        unlock_id=1,
        participant_ids=(20, 30),
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
        level=4,
        encounter_count=6,
        balls_per_participant=3,
        capacity=10,
    )


def _start_result() -> StartSafariResult:
    session = make_session()
    encounter = make_encounter((25,))
    session.publish_encounter(encounter)
    generated_encounter = SafariGeneratedEncounter(
        encounter=encounter,
        event=SafariThematicEvent.NONE,
    )
    return StartSafariResult(
        session=session,
        unlock=_registration_result().unlock,
        generated_encounter=generated_encounter,
    )


@pytest.mark.asyncio
async def test_registration_view_renders_registration_state() -> None:
    view = SafariRegistrationView(
        core=SimpleNamespace(),
        guild_id=10,
        registration_result=_registration_result(),
    )

    embed = view.build_embed()

    assert embed.title.endswith("Safari Registration")
    assert any(field.name == "Level" for field in embed.fields)
    assert any(field.name == "Participants" for field in embed.fields)
    assert [child.label for child in view.children] == [
        "Join Safari",
        "Start Safari",
        "Cancel Safari",
    ]


@pytest.mark.asyncio
async def test_join_button_refreshes_message() -> None:
    result = _registration_result()
    join_registration = AsyncMock(return_value=SimpleNamespace())
    view = SafariRegistrationView(
        core=SimpleNamespace(
            safari_registration_application=SimpleNamespace(
                join=join_registration,
            ),
        ),
        guild_id=10,
        registration_result=result,
    )
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=99),
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.children[0].callback(interaction)

    join_registration.assert_awaited_once_with(10, 99)
    interaction.response.edit_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_button_opens_encounter_view() -> None:
    view = SafariRegistrationView(
        core=SimpleNamespace(
            start_safari_application=SimpleNamespace(
                start=AsyncMock(return_value=_start_result()),
            ),
            safari_registration_application=SimpleNamespace(
                join=AsyncMock(),
                cancel=AsyncMock(),
            ),
        ),
        guild_id=10,
        registration_result=_registration_result(),
    )
    interaction = SimpleNamespace(
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.children[1].callback(interaction)

    kwargs = interaction.response.edit_message.await_args.kwargs
    assert isinstance(
        kwargs["view"],
        SafariEncounterView,
    )
    assert kwargs["attachments"][0].filename == "safari-encounter.png"


@pytest.mark.asyncio
async def test_cancel_button_disables_registration_view() -> None:
    view = SafariRegistrationView(
        core=SimpleNamespace(
            safari_registration_application=SimpleNamespace(
                cancel=AsyncMock(),
            ),
        ),
        guild_id=10,
        registration_result=_registration_result(),
    )
    interaction = SimpleNamespace(
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.children[2].callback(interaction)

    interaction.response.edit_message.assert_awaited_once()
    assert all(child.disabled for child in view.children)
