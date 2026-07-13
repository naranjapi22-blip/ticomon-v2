from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.safari import ResolveSafariCaptureResult
from core.safari import SafariSessionStatus
from interfaces.discord.buttons.pokedex_button import PokedexButton
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from interfaces.discord.views.safari_route_view import SafariRouteView
from interfaces.discord.views.safari_summary import SafariSummaryView
from test.unit.safari.test_session import make_encounter, make_session, make_vote


def _encounter_view(
    remaining_encounters: int = 2,
) -> tuple[SafariEncounterView, object]:
    session = make_session()
    session._route_segments[0].remaining_encounters = remaining_encounters
    encounter = make_encounter((25, 26))
    session.publish_encounter(encounter)
    view = SafariEncounterView(
        core=SimpleNamespace(),
        guild_id=session.guild_id,
        session=session,
    )
    view.message = AsyncMock()
    return view, session


@pytest.mark.asyncio
async def test_encounter_view_renders_slots_and_pokedex_button() -> None:
    view, _ = _encounter_view()

    embed = view.build_embed()

    assert embed.title.startswith("Safari Encounter")
    assert any(field.name == "Map" for field in embed.fields)
    assert any(field.name == "Slot 1" for field in embed.fields)
    assert any(isinstance(child, PokedexButton) for child in view.children)


@pytest.mark.asyncio
async def test_choose_slot_opens_ball_count_view() -> None:
    view, session = _encounter_view()
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.choose_slot(interaction, session.current_encounter.slots[0].id)

    kwargs = interaction.response.send_message.await_args.kwargs
    assert kwargs["ephemeral"] is True
    assert kwargs["view"].__class__.__name__ == "SafariBallCountView"


@pytest.mark.asyncio
async def test_selection_flow_refreshes_the_parent_view() -> None:
    view, session = _encounter_view()
    view.refresh = AsyncMock()
    view.core = SimpleNamespace(
        safari_capture_application=SimpleNamespace(
            select_capture=AsyncMock(
                return_value=SimpleNamespace(
                    session=session,
                    encounter=session.current_encounter,
                    participant=session.participants_by_trainer[1],
                    slot=session.current_encounter.slots[0],
                    balls_selected=1,
                    balls_available=2,
                    selection=SimpleNamespace(
                        slot_id=session.current_encounter.slots[0].id,
                        ball_count=1,
                        is_confirmed=True,
                    ),
                    state=None,
                )
            ),
            confirm_capture_selection=AsyncMock(
                return_value=SimpleNamespace(
                    session=session,
                    encounter=session.current_encounter,
                    participant=session.participants_by_trainer[1],
                    selection=SimpleNamespace(
                        slot_id=session.current_encounter.slots[0].id,
                        ball_count=1,
                        is_confirmed=True,
                    ),
                    balls_spent=1,
                    balls_available=2,
                    state=None,
                )
            ),
            decline_capture=AsyncMock(
                return_value=SimpleNamespace(
                    session=session,
                    encounter=session.current_encounter,
                    participant=session.participants_by_trainer[1],
                    selection=None,
                    balls_available=3,
                    state=None,
                )
            ),
        ),
        safari_route_application=SimpleNamespace(),
        safari_finish_application=SimpleNamespace(),
    )
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.select_balls(interaction, session.current_encounter.slots[0].id, 1)
    await view.confirm_selection(1)
    await view.decline_selection(1)

    assert view.refresh.await_count == 3


@pytest.mark.asyncio
async def test_resolve_encounter_transitions_to_route_view(monkeypatch) -> None:
    view, session = _encounter_view()
    route_vote = make_vote(session.current_segment.zone)
    view.core = SimpleNamespace(
        safari_capture_application=SimpleNamespace(
            close_capture_selection=AsyncMock(),
            resolve_capture=AsyncMock(
                return_value=ResolveSafariCaptureResult(
                    session=session,
                    encounter_resolution=SimpleNamespace(),
                    persisted_result=SimpleNamespace(),
                    slot_results=(),
                    rewards_by_trainer={},
                    balls_committed_by_trainer={},
                    next_session_status=SafariSessionStatus.ROUTE_DECISION,
                )
            ),
        ),
        safari_route_application=SimpleNamespace(
            open_route_vote=AsyncMock(
                return_value=SimpleNamespace(
                    session=session,
                    vote=route_vote,
                    options=route_vote.options,
                )
            ),
        ),
        safari_finish_application=SimpleNamespace(),
    )
    interaction = SimpleNamespace(
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.resolve_encounter(interaction)

    assert isinstance(
        interaction.response.edit_message.await_args.kwargs["view"],
        SafariRouteView,
    )


@pytest.mark.asyncio
async def test_resolve_encounter_transitions_to_summary(monkeypatch) -> None:
    view, session = _encounter_view(remaining_encounters=1)
    monkeypatch.setattr(SafariSummaryView, "build_embeds", lambda self: tuple())
    view.core = SimpleNamespace(
        safari_capture_application=SimpleNamespace(
            close_capture_selection=AsyncMock(),
            resolve_capture=AsyncMock(
                return_value=ResolveSafariCaptureResult(
                    session=session,
                    encounter_resolution=SimpleNamespace(),
                    persisted_result=SimpleNamespace(),
                    slot_results=(),
                    rewards_by_trainer={},
                    balls_committed_by_trainer={},
                    next_session_status=SafariSessionStatus.FINISHED,
                )
            ),
        ),
        safari_route_application=SimpleNamespace(),
        safari_finish_application=SimpleNamespace(
            finish=AsyncMock(return_value=SimpleNamespace(summary=SimpleNamespace()))
        ),
    )
    interaction = SimpleNamespace(
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.resolve_encounter(interaction)

    assert isinstance(
        interaction.response.edit_message.await_args.kwargs["view"],
        SafariSummaryView,
    )
