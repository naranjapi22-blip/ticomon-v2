from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.battle.battle import Battle
from interfaces.discord.cogs.battle_cog import BattleCog
from interfaces.discord.views.battle_selection_view import BattleChallengeView


@pytest.mark.asyncio
async def test_battle_command_sends_challenge_view() -> None:
    battle = Battle.create(
        initiator_trainer_id=1,
        opponent_trainer_id=2,
        created_at=datetime.now(UTC),
    )
    battle._id = 99

    core = SimpleNamespace(
        battle_application_service=SimpleNamespace(
            create_challenge=AsyncMock(return_value=battle),
        ),
    )
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=1),
        send=AsyncMock(return_value=SimpleNamespace()),
    )
    opponent = SimpleNamespace(id=2, bot=False)

    cog = BattleCog(core)
    await cog.battle.callback(cog, ctx, opponent)

    ctx.send.assert_awaited_once()
    sent_kwargs = ctx.send.await_args.kwargs
    assert isinstance(sent_kwargs["view"], BattleChallengeView)
    assert sent_kwargs["view"].battle_id == 99
