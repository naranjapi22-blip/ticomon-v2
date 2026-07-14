from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.safari import ResolveSafariCaptureResult
from core.safari import SafariSessionStatus
from interfaces.discord.buttons.pokedex_button import PokedexButton
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from interfaces.discord.views.safari_route_view import SafariRouteView
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
async def test_encounter_view_builds_attachment_message_and_pokedex_button() -> None:
    view, _ = _encounter_view()

    content, file = await view.build_message()

    assert content.startswith("Safari Encounter")
    assert "Choose a Pokémon and the number of Safari Balls." in content
    assert file.filename == "safari-encounter.png"
    assert [child.__class__.__name__ for child in view.children] == [
        "SafariEncounterSlotSelect",
        "PokedexButton",
    ]
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
async def test_selection_flow_confirms_immediately() -> None:
    view, session = _encounter_view()
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
            decline_capture=AsyncMock(return_value=SimpleNamespace()),
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

    assert interaction.response.send_message.await_count == 1
    assert (
        "Selection confirmed:"
        in interaction.response.send_message.await_args.kwargs["content"]
    )
    assert interaction.response.edit_message.await_count == 0


@pytest.mark.asyncio
async def test_selection_timeout_transitions_to_route_view(monkeypatch) -> None:
    monkeypatch.setattr(
        SafariRouteView,
        "start_route_timer",
        lambda self: None,
    )
    view, session = _encounter_view()
    route_vote = make_vote(session.current_segment.zone)
    view.message = SimpleNamespace(
        channel=SimpleNamespace(send=AsyncMock()),
        edit=AsyncMock(),
    )
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

    await view._resolve_selection_timeout()

    assert view.message.channel.send.await_count == 2
    assert (
        "Encounter Results"
        in view.message.channel.send.await_args_list[0].kwargs["content"]
    )
    assert isinstance(
        view.message.channel.send.await_args_list[1].kwargs["view"],
        SafariRouteView,
    )


@pytest.mark.asyncio
async def test_selection_timeout_transitions_to_summary() -> None:
    view, session = _encounter_view(remaining_encounters=1)
    view.message = SimpleNamespace(
        channel=SimpleNamespace(send=AsyncMock()),
        edit=AsyncMock(),
    )
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
            finish=AsyncMock(
                return_value=SimpleNamespace(
                    summary=SimpleNamespace(
                        safari_map=session.safari_map,
                        weather=session.weather,
                        time_of_day=session.time_of_day,
                        finish_reason=SimpleNamespace(value="completed"),
                        totals=SimpleNamespace(encounters_completed=1),
                        ranking=(),
                    )
                )
            )
        ),
    )

    await view._resolve_selection_timeout()

    assert view.message.channel.send.await_count == 2
    assert view.message.channel.send.await_args_list[1].kwargs["embeds"][0].title == (
        "Safari Complete"
    )


@pytest.mark.asyncio
async def test_encounter_timeout_edits_expired_note() -> None:
    view, _ = _encounter_view()
    view.message = AsyncMock()

    await view.on_timeout()

    assert (
        view.message.edit.await_args.kwargs["content"]
        == "This phase has already ended."
    )


@pytest.mark.asyncio
async def test_expired_encounter_rejects_old_callback() -> None:
    view, session = _encounter_view()
    view._phase_ended = True
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(
            is_done=lambda: False,
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.choose_slot(interaction, session.current_encounter.slots[0].id)

    interaction.response.send_message.assert_awaited_once_with(
        "This phase has already ended.",
        ephemeral=True,
    )
