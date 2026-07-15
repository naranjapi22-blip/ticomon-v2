from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.buttons.opportunity_button import OpportunityButton


@pytest.mark.asyncio
async def test_opportunity_button_reports_english_owner_error():
    session = SimpleNamespace(owner_id=1)
    core = SimpleNamespace(
        get_current_spawn_application=SimpleNamespace(
            get_current=AsyncMock(return_value=session),
        )
    )
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        user=SimpleNamespace(id=2),
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await OpportunityButton(core, 1, "Pokémon 1").callback(interaction)

    interaction.response.send_message.assert_awaited_once_with(
        "Only the trainer who started the !spawn can select a Pokémon.",
        ephemeral=True,
    )
