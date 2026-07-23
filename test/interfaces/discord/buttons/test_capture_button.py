from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest

from core.achievement.unlock_result import AchievementUnlockResult
from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from core.capture.application.capture_application_result import CaptureApplicationResult
from interfaces.discord.buttons.capture_button import (
    CaptureButton,
    _acknowledge_capture,
)


def _expired_interaction_error(code: int) -> discord.NotFound:
    error = discord.NotFound.__new__(discord.NotFound)
    error.code = code
    return error


def _interaction(response) -> SimpleNamespace:
    return SimpleNamespace(
        message=SimpleNamespace(id=101),
        channel_id=202,
        user=SimpleNamespace(id=7),
        response=response,
    )


@pytest.mark.asyncio
async def test_capture_button_acknowledges_before_capture() -> None:
    response = SimpleNamespace(defer=AsyncMock())
    interaction = _interaction(response)
    capture = AsyncMock()
    button = CaptureButton(
        SimpleNamespace(capture_application=SimpleNamespace(capture=capture))
    )

    acknowledged = await _acknowledge_capture(button, interaction)

    assert acknowledged is True
    response.defer.assert_awaited_once_with()
    capture.assert_not_awaited()


@pytest.mark.asyncio
async def test_capture_button_stops_when_interaction_expired(caplog) -> None:
    response = SimpleNamespace(
        defer=AsyncMock(side_effect=_expired_interaction_error(10062))
    )
    interaction = _interaction(response)
    capture = AsyncMock()
    button = CaptureButton(
        SimpleNamespace(capture_application=SimpleNamespace(capture=capture))
    )

    await button.callback(interaction)

    capture.assert_not_awaited()
    assert "message_id=101 channel_id=202 user_id=7" in caplog.text


@pytest.mark.asyncio
async def test_capture_button_does_not_defer_twice_when_already_responded() -> None:
    response = SimpleNamespace(
        is_done=Mock(return_value=True),
        defer=AsyncMock(),
    )
    interaction = _interaction(response)

    acknowledged = await _acknowledge_capture(
        CaptureButton(SimpleNamespace()), interaction
    )

    assert acknowledged is False
    response.defer.assert_not_awaited()


@pytest.mark.asyncio
async def test_capture_button_does_not_capture_after_interaction_responded() -> None:
    response = SimpleNamespace(
        defer=AsyncMock(side_effect=discord.InteractionResponded(_interaction(None))),
    )
    interaction = _interaction(response)
    capture = AsyncMock()
    button = CaptureButton(
        SimpleNamespace(capture_application=SimpleNamespace(capture=capture))
    )

    await button.callback(interaction)

    capture.assert_not_awaited()


@pytest.mark.asyncio
async def test_capture_button_keeps_main_message_and_notifies_dual_type_unlock() -> (
    None
):
    species = SimpleNamespace(
        name="Dracopod",
        pokeapi_id=10000,
        types=["dragon", "poison"],
    )
    creature = SimpleNamespace(
        id=101,
        collection_number=1,
        species=species,
        is_shiny=False,
    )
    attempt = SimpleNamespace(
        capture_ball=SimpleNamespace(name="POKE_BALL"), chance=1.0
    )
    ordinary_reward = CandyBundle.from_amounts(
        CandyAmount(CandyType.DRAGON, 3), CandyAmount(CandyType.POISON, 3)
    )
    achievement_reward = CandyBundle.from_amounts(
        CandyAmount(CandyType.DRAGON, 1), CandyAmount(CandyType.POISON, 1)
    )
    result = CaptureApplicationResult(
        attempt=attempt,
        success=True,
        creature=creature,
        reward=ordinary_reward,
        achievements=(AchievementUnlockResult("first_capture", achievement_reward),),
    )
    followup = SimpleNamespace(send=AsyncMock())
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=7, mention="<@7>"),
        guild=SimpleNamespace(id=9),
        client=Mock(fetch_application_emojis=AsyncMock(return_value=[])),
        response=SimpleNamespace(defer=AsyncMock()),
        followup=followup,
        delete_original_response=AsyncMock(),
    )
    core = SimpleNamespace(
        capture_application=SimpleNamespace(capture=AsyncMock(return_value=result)),
        profile_service=SimpleNamespace(
            get_selected_trainer=AsyncMock(
                return_value=SimpleNamespace(gif="trainer.gif")
            )
        ),
    )

    with patch(
        "interfaces.discord.buttons.capture_button._capture_gif",
        new=AsyncMock(return_value=BytesIO(b"gif")),
    ):
        await CaptureButton(core).callback(interaction)

    assert followup.send.await_count == 2
    main_call, achievement_call = followup.send.await_args_list
    assert "caught Dracopod" in main_call.kwargs["content"]
    assert "Achievement unlocked: First Capture" in achievement_call.args[0]
    assert "Dragon Candy +1" in achievement_call.args[0]
    assert "Poison Candy +1" in achievement_call.args[0]
    interaction.delete_original_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_capture_animation_uses_the_same_oricorio_variant_asset() -> None:
    from interfaces.discord.buttons import capture_button

    creature = SimpleNamespace(
        id=4425,
        collection_number=73,
        species=SimpleNamespace(
            id=741,
            name="oricorio-baile",
            pokeapi_id=741,
            types=["psychic", "flying"],
        ),
        current_form=SimpleNamespace(id=336, name="pau"),
        is_shiny=False,
    )
    trainer = SimpleNamespace(gif="trainer.gif")

    with (
        patch(
            "interfaces.discord.buttons.capture_button.CaptureAnimation"
        ) as animation,
        patch(
            "interfaces.discord.buttons.capture_button.asyncio.to_thread",
            new=AsyncMock(return_value=BytesIO(b"gif")),
        ),
    ):
        await capture_button._capture_gif(creature, trainer, "POKE_BALL")

    assert animation.call_args.kwargs["sprite_path"].endswith(
        "/oricorio/oricorio-pau.gif"
    )


@pytest.mark.asyncio
async def test_capture_gif_falls_back_without_hiding_a_successful_capture(
    caplog,
) -> None:
    from interfaces.discord.buttons import capture_button

    capture_button._MISSING_CAPTURE_RESOURCES.clear()
    creature = SimpleNamespace(
        id=4425,
        collection_number=73,
        species=SimpleNamespace(
            id=741,
            name="oricorio-baile",
            pokeapi_id=741,
            types=["psychic", "flying"],
        ),
        current_form=SimpleNamespace(id=336, name="pau"),
        is_shiny=False,
    )
    trainer = SimpleNamespace(gif="trainer.gif")
    working_animation = SimpleNamespace(gif_bytes=object())

    with (
        patch(
            "interfaces.discord.buttons.capture_button.CaptureAnimation",
            side_effect=(RuntimeError("missing"), working_animation),
        ) as animation,
        patch(
            "interfaces.discord.buttons.capture_button.asyncio.to_thread",
            new=AsyncMock(return_value=BytesIO(b"gif")),
        ),
    ):
        gif = await capture_button._capture_gif(creature, trainer, "POKE_BALL")

    assert gif.getvalue() == b"gif"
    assert (
        animation.call_args_list[0]
        .kwargs["sprite_path"]
        .endswith("/oricorio/oricorio-pau.gif")
    )
    assert animation.call_args_list[1].kwargs["sprite_path"].endswith(
        "/regular/741.gif"
    ) or animation.call_args_list[1].kwargs["sprite_path"].endswith("/regular/741.gif")
    assert caplog.text.count("capture_gif_resource_missing") == 1
    assert "canonical_name=oricorio-baile:pau" in caplog.text


@pytest.mark.asyncio
async def test_capture_button_posts_success_when_the_gif_is_unavailable() -> None:
    species = SimpleNamespace(
        name="Oricorio-Baile",
        pokeapi_id=10101,
        types=["fire", "flying"],
    )
    creature = SimpleNamespace(
        id=4425,
        collection_number=73,
        species=species,
        is_shiny=False,
    )
    result = CaptureApplicationResult(
        attempt=SimpleNamespace(
            capture_ball=SimpleNamespace(name="POKE_BALL"), chance=1.0
        ),
        success=True,
        creature=creature,
        reward=CandyBundle.from_amounts(CandyAmount(CandyType.FIRE, 3)),
        achievements=(),
    )
    followup = SimpleNamespace(send=AsyncMock())
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=8, mention="<@8>"),
        guild=SimpleNamespace(id=9),
        client=Mock(fetch_application_emojis=AsyncMock(return_value=[])),
        response=SimpleNamespace(defer=AsyncMock()),
        followup=followup,
        delete_original_response=AsyncMock(),
    )
    capture = AsyncMock(return_value=result)
    core = SimpleNamespace(
        capture_application=SimpleNamespace(capture=capture),
        profile_service=SimpleNamespace(
            get_selected_trainer=AsyncMock(
                return_value=SimpleNamespace(gif="trainer.gif")
            )
        ),
    )

    with patch(
        "interfaces.discord.buttons.capture_button._capture_gif",
        new=AsyncMock(return_value=None),
    ):
        await CaptureButton(core).callback(interaction)

    capture.assert_awaited_once_with(trainer_id=8, guild_id=9)
    main_call = followup.send.await_args_list[0]
    assert "caught Oricorio-Baile" in main_call.kwargs["content"]
    assert "file" not in main_call.kwargs
    interaction.delete_original_response.assert_awaited_once()
