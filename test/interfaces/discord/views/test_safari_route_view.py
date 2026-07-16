from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.safari.activity_state import SafariActivityTracker
from core.safari.route import SafariRouteOption
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from interfaces.discord.views.safari_route_view import (
    SafariRouteButton,
    SafariRouteView,
)
from test.unit.safari.test_session import make_encounter, make_session, make_vote


@pytest.mark.asyncio
async def test_route_view_renders_options() -> None:
    session = make_session()
    vote = make_vote(session.current_segment.zone)
    view = SafariRouteView(
        core=SimpleNamespace(),
        guild_id=session.guild_id,
        session=session,
        vote=vote,
        options=vote.options,
    )

    assert view.build_content() == (
        "Safari Route Vote\n" "Vote for the next route. Resolves in 30 seconds."
    )
    assert all(isinstance(child, SafariRouteButton) for child in view.children)
    assert [button.label for button in view.children] == [
        view.format_option_label(option) for option in vote.options
    ]
    assert [button.route_option.id for button in view.children] == [
        option.id for option in vote.options
    ]
    assert [button.row for button in view.children] == [0] * len(vote.options)
    assert view.build_file().filename == "safari.png"


@pytest.mark.asyncio
async def test_route_buttons_are_distributed_in_rows_of_five() -> None:
    session = make_session()
    vote = make_vote(session.current_segment.zone)
    options = tuple(
        SafariRouteOption(
            id=f"{option.id}-{index}",
            source_zone=option.source_zone,
            destination_zone=option.destination_zone,
            type_weight_modifiers=option.type_weight_modifiers,
            allowed_events=option.allowed_events,
            narrative_key=f"{option.narrative_key}-{index}",
        )
        for index in range(6)
        for option in (vote.options[index % len(vote.options)],)
    )
    view = SafariRouteView(
        core=SimpleNamespace(),
        guild_id=session.guild_id,
        session=session,
        vote=vote,
        options=options,
    )

    assert [button.row for button in view.children] == [0, 0, 0, 0, 0, 1]


@pytest.mark.asyncio
async def test_route_button_delegates_the_selected_option() -> None:
    session = make_session()
    vote = make_vote(session.current_segment.zone)
    view = SafariRouteView(
        core=SimpleNamespace(),
        guild_id=session.guild_id,
        session=session,
        vote=vote,
        options=vote.options,
    )
    view.cast_vote = AsyncMock()
    interaction = SimpleNamespace()

    await view.children[1].callback(interaction)

    view.cast_vote.assert_awaited_once_with(interaction, vote.options[1].id)


@pytest.mark.asyncio
async def test_cast_vote_is_silent() -> None:
    session = make_session()
    vote = make_vote(session.current_segment.zone)
    cast_route_vote = AsyncMock(
        return_value=SimpleNamespace(
            session=session,
            vote=vote,
            option_id=vote.options[0].id,
            replaced=False,
        )
    )
    view = SafariRouteView(
        core=SimpleNamespace(
            safari_route_application=SimpleNamespace(
                cast_route_vote=cast_route_vote,
                resolve_route_vote=AsyncMock(),
            ),
        ),
        guild_id=session.guild_id,
        session=session,
        vote=vote,
        options=vote.options,
    )
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=101),
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
            defer=AsyncMock(),
        ),
    )

    await view.cast_vote(interaction, vote.options[0].id)

    cast_route_vote.assert_awaited_once_with(
        session.guild_id,
        101,
        vote.options[0].id,
    )
    interaction.response.send_message.assert_not_awaited()
    interaction.response.defer.assert_awaited_once()


@pytest.mark.asyncio
async def test_route_timeout_opens_next_encounter(monkeypatch) -> None:
    monkeypatch.setattr(
        SafariEncounterView,
        "start_selection_timer",
        lambda self: None,
    )
    session = make_session()
    vote = make_vote(session.current_segment.zone)
    next_session = make_session()
    next_session.publish_encounter(make_encounter((7,)))
    old_message = AsyncMock()
    resolve_route_vote = AsyncMock(
        return_value=SimpleNamespace(
            session=next_session,
            vote_result=SimpleNamespace(),
            selected_option=vote.options[0],
            destination_segment=SimpleNamespace(),
            next_encounter=SimpleNamespace(),
        )
    )
    view = SafariRouteView(
        core=SimpleNamespace(
            safari_route_application=SimpleNamespace(
                cast_route_vote=AsyncMock(),
                resolve_route_vote=resolve_route_vote,
            ),
        ),
        guild_id=session.guild_id,
        session=session,
        vote=vote,
        options=vote.options,
    )
    view.message = SimpleNamespace(
        channel=SimpleNamespace(
            id=321,
            send=AsyncMock(),
            fetch_message=AsyncMock(return_value=old_message),
        ),
        edit=AsyncMock(),
    )
    view.core.safari_activity_tracker = SafariActivityTracker()
    view.core.safari_activity_tracker.set_message(session.guild_id, 321, 99)

    await view._resolve_route_timeout()

    old_message.delete.assert_awaited_once()
    assert view.message.channel.send.await_count == 1
    assert isinstance(
        view.message.channel.send.await_args.kwargs["view"],
        SafariEncounterView,
    )
    assert view.message.channel.send.await_args.kwargs["file"].filename == (
        "safari-encounter.png"
    )


@pytest.mark.asyncio
async def test_route_timeout_edits_expired_note() -> None:
    session = make_session()
    vote = make_vote(session.current_segment.zone)
    view = SafariRouteView(
        core=SimpleNamespace(),
        guild_id=session.guild_id,
        session=session,
        vote=vote,
        options=vote.options,
    )
    view.message = AsyncMock()

    await view.on_timeout()

    assert (
        view.message.edit.await_args.kwargs["content"]
        == "This phase has already ended."
    )
