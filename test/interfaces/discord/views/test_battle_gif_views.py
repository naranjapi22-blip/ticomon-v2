from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.battle.engine.battle_result import BattleResult
from core.battle.engine.battle_step import BattleStep, BattleStepType
from interfaces.discord.cogs.battle_gif_experiment_cog import (
    BattleGifExperimentCog,
)
from interfaces.discord.views.battle_gif_arena_view import BattleGifArenaView
from interfaces.discord.views.battle_gif_challenge_view import BattleGifChallengeView


def _snapshot(name: str, hp: int, active_index: int = 0) -> dict:
    return {
        "active_index": active_index,
        "hp": [hp],
        "hp_max": [100],
        "active_name": name,
        "active_move": "Overheat",
    }


def _step(step_type, message, *, side_b_name="Pikachu", side_b_index=0):
    return BattleStep(
        step_type=step_type,
        side_a_name="Alice",
        side_b_name="Bob",
        message=message,
        state_snapshot={
            "Alice": _snapshot("Torchic", 72),
            "Bob": _snapshot(side_b_name, 35, side_b_index),
        },
        pause_seconds=0,
    )


def _core(result, replay):
    return SimpleNamespace(
        battle_application_service=SimpleNamespace(
            get_battle=AsyncMock(return_value=SimpleNamespace(is_ready=True)),
        ),
        battle_execution_service=SimpleNamespace(
            run_battle=AsyncMock(return_value=result),
        ),
        battle_replay_service=SimpleNamespace(replay=replay),
    )


@pytest.mark.asyncio
async def test_batallagif_uses_same_challenge_creation_and_registers_once() -> None:
    create_challenge = AsyncMock(
        return_value=SimpleNamespace(id=10, is_ready=False, has_party=lambda _: False),
    )
    core = SimpleNamespace(
        battle_application_service=SimpleNamespace(
            create_challenge=create_challenge,
        ),
    )
    cog = BattleGifExperimentCog(core)
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=1),
        send=AsyncMock(return_value=SimpleNamespace()),
    )
    opponent = SimpleNamespace(id=2, bot=False)

    await cog.batalla_gif.callback(cog, ctx, opponent)

    create_challenge.assert_awaited_once()
    assert ctx.send.await_args.kwargs["view"].__class__ is BattleGifChallengeView
    assert [command.name for command in cog.get_commands()] == ["batallagif"]


@pytest.mark.asyncio
async def test_gif_challenge_switches_to_gif_arena_when_ready() -> None:
    message = AsyncMock()
    view = BattleGifChallengeView(SimpleNamespace(), 10, 1, 2)
    view.message = message

    battle = SimpleNamespace(
        is_ready=True,
        has_party=lambda trainer_id: trainer_id in {1, 2},
    )
    await view.refresh_display(battle)

    assert isinstance(message.edit.await_args.kwargs["view"], BattleGifArenaView)


@pytest.mark.asyncio
async def test_gif_arena_runs_once_and_updates_two_gif_attachments(
    monkeypatch,
) -> None:
    steps = (
        _step(BattleStepType.START, "Battle started."),
        _step(BattleStepType.MOVE, "Alice's Torchic uses Overheat!"),
        _step(BattleStepType.DAMAGE, "Torchic uses Overheat!"),
        _step(BattleStepType.ATTACK, "It dealt 40 damage!"),
        _step(
            BattleStepType.SWITCH,
            "Bob sent out Charizard!",
            side_b_name="Charizard",
            side_b_index=1,
        ),
        _step(
            BattleStepType.VICTORY,
            "Alice wins the battle!",
            side_b_name="Charizard",
            side_b_index=1,
        ),
    )
    result = BattleResult(steps=steps, winner_side_name="Alice", winner_trainer_id=1)

    async def replay(result_steps, callback):
        for step in result_steps:
            await callback(step, (step.message,))

    core = _core(result, replay)
    view = BattleGifArenaView(core, 10, 1, 2)
    view.message = AsyncMock()
    view._load_fighter_metadata = AsyncMock(
        side_effect=lambda: (
            setattr(view, "_side_a_meta", [(25, False)]),
            setattr(view, "_side_b_meta", [(6, False), (150, False)]),
        ),
    )
    monkeypatch.setattr(
        "interfaces.discord.views.battle_gif_arena_view.resolve_trainer_display_name",
        AsyncMock(side_effect=["Alice", "Bob"]),
    )
    loads = []

    def fake_load(url):
        loads.append(url)
        return b"GIF89a"

    monkeypatch.setattr(BattleGifArenaView, "_load_gif_bytes", staticmethod(fake_load))
    interaction = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        client=object(),
        guild=object(),
    )

    await view.children[0].callback(interaction)
    await view.children[0].callback(interaction)

    core.battle_execution_service.run_battle.assert_awaited_once()
    assert len(loads) == 3
    attachment_edits = [
        call.kwargs["attachments"]
        for call in view.message.edit.await_args_list
        if "attachments" in call.kwargs
    ]
    assert len(attachment_edits) == 2
    assert all(len(files) == 2 for files in attachment_edits)
    assert [file.filename for file in attachment_edits[0]] == [
        "player.gif",
        "opponent.gif",
    ]
    descriptions = [
        call.kwargs["embed"].description
        for call in view.message.edit.await_args_list
        if "embed" in call.kwargs
    ]
    assert any(
        "Torchic uses Overheat!\nIt dealt 40 damage!" in text for text in descriptions
    )
    assert descriptions[-1].startswith("🏆 Battle Complete\nAlice wins!")
    assert all("Alice's Torchic" not in text for text in descriptions)
    assert all("Alice wins!" not in text for text in descriptions[:-1])
    assert all("ffmpeg" not in str(call) for call in view.message.edit.await_args_list)


@pytest.mark.asyncio
async def test_gif_arena_reports_display_failure_without_rerunning_battle(
    monkeypatch,
) -> None:
    result = BattleResult(steps=(), winner_side_name="Alice", winner_trainer_id=1)

    async def replay(result_steps, callback):
        raise RuntimeError("Discord upload failed")

    core = _core(result, replay)
    view = BattleGifArenaView(core, 10, 1, 2)
    view.message = AsyncMock()
    view._load_fighter_metadata = AsyncMock(
        side_effect=lambda: (
            setattr(view, "_side_a_meta", [(25, False)]),
            setattr(view, "_side_b_meta", [(6, False)]),
        ),
    )
    monkeypatch.setattr(
        "interfaces.discord.views.battle_gif_arena_view.resolve_trainer_display_name",
        AsyncMock(side_effect=["Alice", "Bob"]),
    )
    interaction = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        client=object(),
        guild=None,
    )

    await view.children[0].callback(interaction)

    core.battle_execution_service.run_battle.assert_awaited_once()
    interaction.followup.send.assert_awaited_once()
