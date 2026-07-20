from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image, ImageDraw

from core.battle.engine.battle_result import BattleResult
from core.battle.engine.battle_step import BattleStep, BattleStepType
from interfaces.discord.views.battle_video_arena_view import BattleVideoArenaView
from interfaces.discord.views.battle_video_challenge_view import (
    BattleVideoChallengeView,
)
from rendering.battle.assets import HEIGHT, WIDTH
from rendering.battle.frame_state import BattleFrameState
from rendering.battle.gif_assets import GifSequence
from rendering.battle.video_renderer import (
    DEFAULT_SPECIAL_ATTACK_COLOR,
    SPECIAL_ATTACK_COLORS,
    _AnimatedSprite,
    _animation_frames,
    _draw_frame,
    _special_attack_color,
    _step_duration,
)


def _snapshot(name: str, hp: int, move: str) -> dict:
    return {
        "active_index": 0,
        "hp": [hp],
        "hp_max": [100],
        "active_name": name,
        "active_move": move,
    }


def _sprites() -> dict[tuple[int, bool, bool], _AnimatedSprite]:
    image = Image.new("RGBA", (40, 40), (255, 255, 255, 255))
    sequence = _AnimatedSprite(GifSequence((image,), (100,)))
    return {
        (25, False, True): sequence,
        (6, False, False): sequence,
    }


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
    assert message.edit.await_args.kwargs["embed"].description == (
        "Battle video ready."
    )
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


def test_video_renderer_puts_winner_only_in_final_scene() -> None:
    step = BattleStep(
        step_type=BattleStepType.VICTORY,
        side_a_name="Alice",
        side_b_name="Bob",
        message="Alice wins the battle!",
        state_snapshot={
            "Alice": {
                "active_index": 0,
                "hp": [100],
                "hp_max": [100],
                "active_name": "Pikachu",
                "active_move": "Thunderbolt",
            },
            "Bob": {
                "active_index": 0,
                "hp": [0],
                "hp_max": [100],
                "active_name": "Charizard",
                "active_move": "Flamethrower",
            },
        },
    )
    result = BattleResult(
        steps=(step,),
        winner_side_name="Alice",
        winner_trainer_id=1,
    )

    frames = _animation_frames(
        result,
        {"Alice": ((25, False),), "Bob": ((6, False),)},
        "Alice",
        "Bob",
    )

    assert frames[0][1].attack_line == "🏆 Battle Complete\nAlice wins!"


def test_video_renderer_uses_one_second_for_every_attack() -> None:
    assert _step_duration(BattleStepType.ATTACK) == 1.00
    assert _step_duration(BattleStepType.START) == 1.0
    assert _step_duration(BattleStepType.SWITCH) == 0.8
    assert _step_duration(BattleStepType.VICTORY) == 2.4


def test_special_attack_color_uses_fire_type() -> None:
    assert (
        _special_attack_color("Alice's Pikachu uses Flamethrower!")
        == SPECIAL_ATTACK_COLORS["fire"]
    )


def test_special_attack_color_distinguishes_water_type() -> None:
    assert (
        _special_attack_color("Alice's Pikachu uses Surf!")
        == SPECIAL_ATTACK_COLORS["water"]
    )
    assert SPECIAL_ATTACK_COLORS["water"] != SPECIAL_ATTACK_COLORS["fire"]


def test_special_attack_color_falls_back_for_unresolved_move() -> None:
    assert (
        _special_attack_color("Alice's Pikachu attacks!")
        == DEFAULT_SPECIAL_ATTACK_COLOR
    )


def test_physical_attack_does_not_select_a_special_attack_color() -> None:
    steps = (
        BattleStep(
            step_type=BattleStepType.MOVE,
            side_a_name="Alice",
            side_b_name="Bob",
            message="Alice's Pikachu uses Tackle!",
            state_snapshot={
                "Alice": _snapshot("Pikachu", 100, "Tackle"),
                "Bob": _snapshot("Charizard", 100, "Flamethrower"),
            },
        ),
        BattleStep(
            step_type=BattleStepType.ATTACK,
            side_a_name="Alice",
            side_b_name="Bob",
            message="It dealt 20 damage!",
            state_snapshot={
                "Alice": _snapshot("Pikachu", 100, "Tackle"),
                "Bob": _snapshot("Charizard", 80, "Flamethrower"),
            },
        ),
    )
    frames = _animation_frames(
        BattleResult(steps=steps, winner_side_name="Alice"),
        {"Alice": ((25, False),), "Bob": ((6, False),)},
        "Alice",
        "Bob",
    )

    assert frames[0][2] == "physical_attack"
    assert frames[0][3] is None


def test_special_target_stays_still_until_impact(monkeypatch) -> None:
    previous = BattleFrameState(
        side_a_name="Alice",
        side_b_name="Bob",
        side_a_active_name="Pikachu",
        side_b_active_name="Charizard",
        side_a_hp=100,
        side_a_hp_max=100,
        side_b_hp=100,
        side_b_hp_max=100,
        side_a_pokeapi_id=25,
        side_b_pokeapi_id=6,
        side_a_shiny=False,
        side_b_shiny=False,
        attack_line="",
        turn_number=1,
    )
    current = replace(previous, side_b_hp=60)
    positions: list[int] = []

    def capture_position(image, sprite, *, center_x, bottom_y, max_width, max_height):
        positions.append(center_x)

    monkeypatch.setattr(
        "rendering.battle.video_renderer._paste_centered",
        capture_position,
    )
    for progress in (0.5, 0.8):
        positions.clear()
        _draw_frame(
            background=Image.new("RGBA", (WIDTH, HEIGHT), "black"),
            frame=current,
            previous=previous,
            step_type=BattleStepType.ATTACK,
            progress=progress,
            elapsed_seconds=0,
            sprites=_sprites(),
            animation="special_attack",
        )
        if progress == 0.5:
            assert positions[1] == 800
        else:
            assert positions[1] != 800


def test_final_winner_text_is_centered(monkeypatch) -> None:
    frame = BattleFrameState(
        side_a_name="Alice",
        side_b_name="Bob",
        side_a_active_name="Pikachu",
        side_b_active_name="Charizard",
        side_a_hp=100,
        side_a_hp_max=100,
        side_b_hp=0,
        side_b_hp_max=100,
        side_a_pokeapi_id=25,
        side_b_pokeapi_id=6,
        side_a_shiny=False,
        side_b_shiny=False,
        attack_line="🏆 Battle Complete\nAlice wins!",
        turn_number=1,
    )
    calls = []
    original = ImageDraw.ImageDraw.multiline_text

    def capture_text(draw, xy, text, *args, **kwargs):
        calls.append((xy, kwargs.get("anchor"), text))
        return original(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "multiline_text", capture_text)
    _draw_frame(
        background=Image.new("RGBA", (WIDTH, HEIGHT), "black"),
        frame=frame,
        previous=frame,
        step_type=BattleStepType.VICTORY,
        progress=0,
        elapsed_seconds=0,
        sprites=_sprites(),
        animation=None,
    )

    assert calls[-1] == ((WIDTH // 2, HEIGHT // 2), "mm", frame.attack_line)


def test_visual_attack_caption_removes_trainer_and_duplicate_move() -> None:
    steps = (
        BattleStep(
            step_type=BattleStepType.MOVE,
            side_a_name="Jorroco",
            side_b_name="Bob",
            message="Jorroco's Torchic uses Overheat!",
            state_snapshot={
                "Jorroco": _snapshot("Torchic", 100, "Overheat"),
                "Bob": _snapshot("Charizard", 100, "Flamethrower"),
            },
        ),
        BattleStep(
            step_type=BattleStepType.DAMAGE,
            side_a_name="Jorroco",
            side_b_name="Bob",
            message="Torchic uses Overheat!",
            state_snapshot={
                "Jorroco": _snapshot("Torchic", 100, "Overheat"),
                "Bob": _snapshot("Charizard", 100, "Flamethrower"),
            },
        ),
        BattleStep(
            step_type=BattleStepType.ATTACK,
            side_a_name="Jorroco",
            side_b_name="Bob",
            message="It dealt 40 damage!",
            state_snapshot={
                "Jorroco": _snapshot("Torchic", 100, "Overheat"),
                "Bob": _snapshot("Charizard", 60, "Flamethrower"),
            },
        ),
    )
    result = BattleResult(steps=steps, winner_side_name="Jorroco")

    caption = _animation_frames(
        result,
        {"Jorroco": ((25, False),), "Bob": ((6, False),)},
        "Jorroco",
        "Bob",
    )[0][1].attack_line

    assert caption == "Torchic uses Overheat! It dealt 40 damage!"
    assert caption.count("Torchic uses Overheat") == 1
    assert "Jorroco" not in caption
