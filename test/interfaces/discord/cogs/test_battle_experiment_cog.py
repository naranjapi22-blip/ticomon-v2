from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.battle.battle import Battle
from interfaces.discord.cogs.battle_experiment_cog import BattleExperimentCog
from interfaces.discord.views.battle_video_challenge_view import (
    BattleVideoChallengeView,
)


@pytest.mark.asyncio
async def test_batalla_command_creates_video_challenge_view() -> None:
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

    await BattleExperimentCog(core).batalla.callback(
        BattleExperimentCog(core),
        ctx,
        SimpleNamespace(id=2, bot=False),
    )

    ctx.send.assert_awaited_once()
    assert isinstance(ctx.send.await_args.kwargs["view"], BattleVideoChallengeView)
