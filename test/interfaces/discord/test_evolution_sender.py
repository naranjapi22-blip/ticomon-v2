from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import interfaces.discord.evolution_sender as evolution_sender
from interfaces.discord.evolution_sender import _achievement_text


def test_evolution_notification_includes_nature_mint_reward() -> None:
    result = SimpleNamespace(
        achievements=(
            SimpleNamespace(
                achievement_id="first_evolution",
                rewarded_candies={},
                rewarded_mints=1,
            ),
        )
    )

    assert "Nature Mint +1" in _achievement_text(result)


@pytest.mark.asyncio
async def test_evolution_result_survives_achievement_presentation_failure(monkeypatch):
    result = SimpleNamespace(
        previous_species=SimpleNamespace(id=1, name="bulbasaur"),
        evolved_species=SimpleNamespace(id=2, name="ivysaur"),
        achievements=(SimpleNamespace(achievement_id="first_evolution"),),
    )
    send = AsyncMock()
    monkeypatch.setattr(
        evolution_sender,
        "format_unlocks",
        lambda _achievements: (_ for _ in ()).throw(RuntimeError("broken format")),
    )
    monkeypatch.setattr(evolution_sender, "_build_animation", lambda _result: "gif")

    await evolution_sender.send_evolution_result(send, result)

    send.assert_awaited_once()
    assert "Evolution successful!" in send.await_args.kwargs["content"]


@pytest.mark.asyncio
async def test_deferred_evolution_result_edits_original_response(monkeypatch):
    result = SimpleNamespace(
        previous_species=SimpleNamespace(id=1, name="bulbasaur"),
        evolved_species=SimpleNamespace(id=2, name="ivysaur"),
        achievements=(),
    )
    interaction = SimpleNamespace(
        response=SimpleNamespace(edit_message=AsyncMock()),
        edit_original_response=AsyncMock(),
    )
    monkeypatch.setattr(evolution_sender, "_build_animation", lambda _result: "gif")

    await evolution_sender.edit_evolution_result(interaction, result)

    interaction.edit_original_response.assert_awaited_once()
    interaction.response.edit_message.assert_not_awaited()
