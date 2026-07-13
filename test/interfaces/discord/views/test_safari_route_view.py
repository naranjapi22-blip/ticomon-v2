from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

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

    embed = view.build_embed()

    assert embed.title == "Safari Route Vote"
    assert any(field.name == "Votes" for field in embed.fields)
    assert view.children[0].__class__.__name__ == "SafariRouteOptionSelect"
    assert view.children[1].__class__.__name__ == "SafariRouteResolveButton"


@pytest.mark.asyncio
async def test_cast_vote_refreshes_route_view() -> None:
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
    view.refresh = AsyncMock()
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=101),
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.cast_vote(interaction, vote.options[0].id)

    cast_route_vote.assert_awaited_once_with(
        session.guild_id,
        101,
        vote.options[0].id,
    )
    interaction.response.send_message.assert_awaited_once()
    assert view.refresh.await_count == 1


@pytest.mark.asyncio
async def test_resolve_route_opens_next_encounter() -> None:
    session = make_session()
    vote = make_vote(session.current_segment.zone)
    next_session = make_session()
    next_session.publish_encounter(make_encounter((7,)))
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
    interaction = SimpleNamespace(
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.resolve_route(interaction)

    assert isinstance(
        interaction.response.edit_message.await_args.kwargs["view"],
        SafariEncounterView,
    )
