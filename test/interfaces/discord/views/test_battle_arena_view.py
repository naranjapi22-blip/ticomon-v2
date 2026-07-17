from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from interfaces.discord.views.battle_arena_view import (
    BattleArenaView,
    _is_transient_discord_error,
)


def test_is_transient_discord_error_for_server_error() -> None:
    error = discord.DiscordServerError(
        SimpleNamespace(status=503, reason="Service Unavailable"),
        "503: Service Unavailable",
    )

    assert _is_transient_discord_error(error)


def test_is_transient_discord_error_for_rate_limit() -> None:
    error = discord.HTTPException(
        SimpleNamespace(status=429, reason="Too Many Requests"),
        "rate limited",
    )

    assert _is_transient_discord_error(error)


def test_is_transient_discord_error_for_permanent_failure() -> None:
    error = discord.HTTPException(
        SimpleNamespace(status=400, reason="Bad Request"),
        "bad request",
    )

    assert not _is_transient_discord_error(error)


@pytest.mark.asyncio
async def test_edit_replay_message_retries_transient_discord_errors() -> None:
    view = BattleArenaView(
        core=SimpleNamespace(),
        battle_id=1,
        initiator_id=10,
        opponent_id=20,
    )
    view.message = AsyncMock()
    view.message.edit = AsyncMock(
        side_effect=[
            discord.DiscordServerError(
                SimpleNamespace(status=503, reason="Service Unavailable"),
                "503: Service Unavailable",
            ),
            None,
        ],
    )

    embed = discord.Embed(title="Battle")
    await view._edit_replay_message(embed=embed)

    assert view.message.edit.await_count == 2
    second_call = view.message.edit.await_args_list[1].kwargs
    assert "attachments" not in second_call
