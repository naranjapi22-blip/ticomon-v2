from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.buttons.pokedex_button import PokedexButton
from test.factories import create_species


@pytest.mark.asyncio
async def test_safari_pokedex_button_reuses_repository_checks() -> None:
    species = (create_species(id=1), create_species(id=2))
    species_repository = SimpleNamespace(
        get_many=AsyncMock(return_value=species),
    )
    creature_repository = SimpleNamespace(
        has_species=AsyncMock(side_effect=[True, False]),
    )
    core = SimpleNamespace(
        species_repository=species_repository,
        creature_repository=creature_repository,
    )
    button = PokedexButton(core, species_ids=(1, 2))
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=42),
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await button.callback(interaction)

    species_repository.get_many.assert_awaited_once_with((1, 2))
    assert creature_repository.has_species.await_count == 2
    embed = interaction.response.send_message.await_args.kwargs["embed"]
    assert "Caught" in embed.description
    assert "Missing" in embed.description
