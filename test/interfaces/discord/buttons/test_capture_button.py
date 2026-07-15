from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from core.achievement.unlock_result import AchievementUnlockResult
from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from core.capture.application.capture_application_result import CaptureApplicationResult
from interfaces.discord.buttons.capture_button import CaptureButton


@pytest.mark.asyncio
async def test_capture_button_keeps_main_message_and_notifies_dual_type_unlock() -> (
    None
):
    species = SimpleNamespace(name="Dracopod", types=["dragon", "poison"])
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

    with (
        patch(
            "interfaces.discord.buttons.capture_button.get_capture_sprite",
            return_value="sprite",
        ),
        patch(
            "interfaces.discord.buttons.capture_button.CaptureAnimation"
        ) as animation,
        patch(
            "interfaces.discord.buttons.capture_button.asyncio.to_thread",
            new=AsyncMock(return_value=BytesIO(b"gif")),
        ),
    ):
        animation.return_value.gif_bytes.return_value = b"gif"
        await CaptureButton(core).callback(interaction)

    assert followup.send.await_count == 2
    main_call, achievement_call = followup.send.await_args_list
    assert "caught Dracopod" in main_call.kwargs["content"]
    assert "Achievement unlocked: First Capture" in achievement_call.args[0]
    assert "Dragon Candy +1" in achievement_call.args[0]
    assert "Poison Candy +1" in achievement_call.args[0]
    interaction.delete_original_response.assert_awaited_once()
