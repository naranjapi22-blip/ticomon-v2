from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.safari.activity_state import SafariActivityTracker
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from interfaces.discord.views.safari_route_view import SafariRouteView
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
    assert [option.label for option in view.children[0].options] == [
        f"{'Stay at' if option.stays_in_same_zone else 'Advance to'} "
        f"{option.destination_zone.value.replace('_', ' ').title()}"
        for option in vote.options
    ]
    assert all(":" not in option.label for option in view.children[0].options)
    assert view.children[0].__class__.__name__ == "SafariRouteOptionSelect"


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
