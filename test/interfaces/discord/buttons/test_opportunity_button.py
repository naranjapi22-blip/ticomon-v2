from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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


@pytest.mark.asyncio
async def test_opportunity_button_attaches_the_selected_variant_gif() -> None:
    selected = SimpleNamespace(
        species=SimpleNamespace(
            id=741,
            name="oricorio-baile",
            pokeapi_id=741,
            spawn_rarity=SimpleNamespace(name="STANDARD"),
        ),
        initial_form=SimpleNamespace(id=336, name="pau"),
        is_shiny=False,
    )
    session = SimpleNamespace(owner_id=1, selected_opportunity=selected)
    steps = []

    async def select(**_kwargs) -> None:
        steps.append("select")

    async def defer() -> None:
        steps.append("defer")

    core = SimpleNamespace(
        get_current_spawn_application=SimpleNamespace(
            get_current=AsyncMock(return_value=session),
        ),
        select_opportunity_application=SimpleNamespace(select_opportunity=select),
    )
    gif_file = SimpleNamespace(filename="spawn.gif")
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(defer=AsyncMock(side_effect=defer)),
        edit_original_response=AsyncMock(),
        original_response=AsyncMock(return_value=SimpleNamespace()),
    )

    with patch(
        "interfaces.discord.buttons.opportunity_button._opportunity_gif_file",
        new=AsyncMock(return_value=gif_file),
    ) as gif:
        await OpportunityButton(core, 1, "Pokemon 1").callback(interaction)

    interaction.response.defer.assert_awaited_once()
    assert steps == ["defer", "select"]
    gif.assert_awaited_once_with(selected)
    kwargs = interaction.edit_original_response.await_args.kwargs
    assert kwargs["attachments"] == [gif_file]
    assert kwargs["embed"].image.url == "attachment://spawn.gif"


@pytest.mark.asyncio
async def test_opportunity_gif_falls_back_to_the_species_asset(
    monkeypatch, caplog
) -> None:
    from interfaces.discord.buttons import opportunity_button

    opportunity_button._MISSING_SPAWN_RESOURCES.clear()
    opportunity = SimpleNamespace(
        species=SimpleNamespace(id=741, name="oricorio-baile", pokeapi_id=741),
        initial_form=SimpleNamespace(id=336, name="pau"),
        is_shiny=False,
    )
    fallback_file = SimpleNamespace(filename="spawn.gif")
    download = AsyncMock(
        side_effect=(
            RuntimeError("missing"),
            fallback_file,
            RuntimeError("missing"),
            fallback_file,
        )
    )
    monkeypatch.setattr(opportunity_button, "download_gif_file", download)

    assert await opportunity_button._opportunity_gif_file(opportunity) is fallback_file
    assert await opportunity_button._opportunity_gif_file(opportunity) is fallback_file
    assert download.await_args_list[0].args[0].endswith("/oricorio/oricorio-pau.gif")
    assert download.await_args_list[1].args[0].endswith("/regular/741.gif")
    assert caplog.text.count("spawn_gif_resource_missing") == 1
    assert "canonical_name=oricorio-baile:pau" in caplog.text
