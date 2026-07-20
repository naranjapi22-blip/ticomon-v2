from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.battle.engine.battle_result import BattleResult
from interfaces.discord.views.battle_video_arena_view import BattleVideoArenaView
from interfaces.discord.views.battle_video_challenge_view import (
    BattleVideoChallengeView,
)


@pytest.mark.asyncio
async def test_video_challenge_switches_to_video_arena_when_ready() -> None:
    message = AsyncMock()
    battle = SimpleNamespace(
        is_ready=True,
        has_party=lambda trainer_id: True,
    )
    view = BattleVideoChallengeView(SimpleNamespace(), 10, 1, 2)
    view.message = message

    await view.refresh_display(battle)

    sent_view = message.edit.await_args.kwargs["view"]
    assert isinstance(sent_view, BattleVideoArenaView)


@pytest.mark.asyncio
async def test_video_arena_runs_battle_renders_and_cleans_temp_file(
    monkeypatch,
) -> None:
    battle = SimpleNamespace(is_ready=True)
    result = BattleResult(steps=(), winner_side_name="Alice", winner_trainer_id=1)
    run_battle = AsyncMock(return_value=result)
    message = AsyncMock()
    core = SimpleNamespace(
        battle_application_service=SimpleNamespace(
            get_battle=AsyncMock(return_value=battle),
        ),
        battle_execution_service=SimpleNamespace(run_battle=run_battle),
        battle_renderer=SimpleNamespace(
            get_background_for_battle=lambda battle_id: object(),
        ),
    )
    view = BattleVideoArenaView(core, 10, 1, 2)
    view.message = message
    view._load_fighter_metadata = AsyncMock(
        side_effect=lambda: (
            setattr(view, "_side_a_meta", [(25, False)]),
            setattr(view, "_side_b_meta", [(6, False)]),
        ),
    )
    interaction = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        client=object(),
        guild=object(),
    )

    captured_path = None
    captured_result = None

    def fake_render(*args):
        nonlocal captured_path, captured_result
        captured_result = args[0]
        captured_path = args[-1]
        captured_path.write_bytes(b"mp4")

    monkeypatch.setattr(
        "interfaces.discord.views.battle_video_arena_view.resolve_trainer_display_name",
        AsyncMock(side_effect=["Alice", "Bob"]),
    )
    monkeypatch.setattr(
        "interfaces.discord.views.battle_video_arena_view.render_battle_video",
        fake_render,
    )

    await view.children[0].callback(interaction)
    second_interaction = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        client=object(),
        guild=object(),
    )
    await view.children[0].callback(second_interaction)

    run_battle.assert_awaited_once()
    assert captured_result is result
    assert captured_path is not None
    assert not captured_path.exists()
    assert message.edit.await_count == 2
    second_interaction.response.defer.assert_not_awaited()


@pytest.mark.asyncio
async def test_video_arena_reports_renderer_failure(monkeypatch) -> None:
    battle = SimpleNamespace(is_ready=True)
    view = BattleVideoArenaView(
        SimpleNamespace(
            battle_application_service=SimpleNamespace(
                get_battle=AsyncMock(return_value=battle),
            ),
            battle_execution_service=SimpleNamespace(
                run_battle=AsyncMock(
                    return_value=BattleResult(
                        steps=(),
                        winner_side_name="Alice",
                        winner_trainer_id=1,
                    ),
                ),
            ),
            battle_renderer=SimpleNamespace(
                get_background_for_battle=lambda battle_id: object(),
            ),
        ),
        10,
        1,
        2,
    )
    view._load_fighter_metadata = AsyncMock()
    interaction = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        client=object(),
        guild=object(),
    )

    monkeypatch.setattr(
        "interfaces.discord.views.battle_video_arena_view.resolve_trainer_display_name",
        AsyncMock(side_effect=["Alice", "Bob"]),
    )
    monkeypatch.setattr(
        "interfaces.discord.views.battle_video_arena_view.render_battle_video",
        lambda *args: (_ for _ in ()).throw(RuntimeError("render failed")),
    )

    await view.children[0].callback(interaction)

    interaction.followup.send.assert_awaited_once_with(
        "⚠️ Battle finished, but the video could not be generated.",
        ephemeral=True,
    )
