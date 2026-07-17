from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.buttons.opportunity_button import OpportunityButton
from interfaces.discord.images import get_opportunity_gif, get_species_gif


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
async def test_opportunity_button_uses_direct_url_for_base_spawn(
    monkeypatch,
) -> None:
    selected = SimpleNamespace(
        species=SimpleNamespace(
            id=37,
            name="vulpix",
            pokeapi_id=37,
            spawn_rarity=SimpleNamespace(name="STANDARD"),
        ),
        initial_form=None,
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
    expected_url = get_species_gif(37, False)
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(defer=AsyncMock(side_effect=defer)),
        edit_original_response=AsyncMock(),
        original_response=AsyncMock(return_value=SimpleNamespace()),
    )

    download = AsyncMock()
    monkeypatch.setattr("interfaces.discord.images.download_gif_file", download)
    monkeypatch.setattr(
        "interfaces.discord.buttons.opportunity_button._spawn_gif_url",
        AsyncMock(return_value=expected_url),
    )

    await OpportunityButton(core, 1, "Pokemon 1").callback(interaction)

    interaction.response.defer.assert_awaited_once()
    assert steps == ["defer", "select"]
    download.assert_not_awaited()
    kwargs = interaction.edit_original_response.await_args.kwargs
    assert kwargs["attachments"] == []
    assert kwargs["embed"].image.url == expected_url


@pytest.mark.asyncio
async def test_opportunity_button_uses_shiny_url_for_shiny_spawn(
    monkeypatch,
) -> None:
    selected = SimpleNamespace(
        species=SimpleNamespace(
            id=37,
            name="vulpix",
            pokeapi_id=37,
            spawn_rarity=SimpleNamespace(name="STANDARD"),
        ),
        initial_form=None,
        is_shiny=True,
    )
    session = SimpleNamespace(owner_id=1, selected_opportunity=selected)
    core = SimpleNamespace(
        get_current_spawn_application=SimpleNamespace(
            get_current=AsyncMock(return_value=session),
        ),
        select_opportunity_application=SimpleNamespace(select_opportunity=AsyncMock()),
    )
    expected_url = get_species_gif(37, True)
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(defer=AsyncMock()),
        edit_original_response=AsyncMock(),
        original_response=AsyncMock(return_value=SimpleNamespace()),
    )

    monkeypatch.setattr(
        "interfaces.discord.buttons.opportunity_button._spawn_gif_url",
        AsyncMock(return_value=expected_url),
    )

    await OpportunityButton(core, 1, "Pokemon 1").callback(interaction)

    kwargs = interaction.edit_original_response.await_args.kwargs
    assert kwargs["attachments"] == []
    assert kwargs["embed"].image.url == expected_url


@pytest.mark.asyncio
async def test_opportunity_button_uses_variant_url_when_available(
    monkeypatch,
) -> None:
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
    core = SimpleNamespace(
        get_current_spawn_application=SimpleNamespace(
            get_current=AsyncMock(return_value=session),
        ),
        select_opportunity_application=SimpleNamespace(select_opportunity=AsyncMock()),
    )
    expected_url = get_opportunity_gif(selected)
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(defer=AsyncMock()),
        edit_original_response=AsyncMock(),
        original_response=AsyncMock(return_value=SimpleNamespace()),
    )

    monkeypatch.setattr(
        "interfaces.discord.buttons.opportunity_button._spawn_gif_url",
        AsyncMock(return_value=expected_url),
    )
    monkeypatch.setattr(
        "interfaces.discord.images.download_gif_file",
        AsyncMock(),
    )

    await OpportunityButton(core, 1, "Pokemon 1").callback(interaction)

    kwargs = interaction.edit_original_response.await_args.kwargs
    assert kwargs["attachments"] == []
    assert kwargs["embed"].image.url == expected_url
    assert kwargs["embed"].image.url.endswith(
        "/showdown_variantes/oricorio/oricorio-pau.gif"
    )


@pytest.mark.asyncio
async def test_opportunity_gif_url_falls_back_to_the_species_asset(
    monkeypatch, caplog
) -> None:
    from interfaces.discord.buttons import opportunity_button

    opportunity_button._MISSING_SPAWN_RESOURCES.clear()
    opportunity = SimpleNamespace(
        species=SimpleNamespace(id=741, name="oricorio-baile", pokeapi_id=741),
        initial_form=SimpleNamespace(id=336, name="pau"),
        is_shiny=False,
    )
    species_url = get_species_gif(741, False)

    def resource_exists(url: str) -> bool:
        return url == species_url

    monkeypatch.setattr(opportunity_button, "_resource_exists", resource_exists)

    assert await opportunity_button._spawn_gif_url(opportunity) == species_url
    assert await opportunity_button._spawn_gif_url(opportunity) == species_url
    assert caplog.text.count("spawn_gif_resource_missing") == 1
    assert "canonical_name=oricorio-baile:pau" in caplog.text


@pytest.mark.asyncio
async def test_opportunity_button_sends_spawn_without_image_when_unavailable(
    monkeypatch,
) -> None:
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
    core = SimpleNamespace(
        get_current_spawn_application=SimpleNamespace(
            get_current=AsyncMock(return_value=session),
        ),
        select_opportunity_application=SimpleNamespace(select_opportunity=AsyncMock()),
    )
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(defer=AsyncMock()),
        edit_original_response=AsyncMock(),
        original_response=AsyncMock(return_value=SimpleNamespace()),
    )

    monkeypatch.setattr(
        "interfaces.discord.buttons.opportunity_button._spawn_gif_url",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "interfaces.discord.images.download_gif_file",
        AsyncMock(),
    )

    await OpportunityButton(core, 1, "Pokemon 1").callback(interaction)

    kwargs = interaction.edit_original_response.await_args.kwargs
    assert kwargs["attachments"] == []
    assert "image" not in kwargs["embed"].to_dict()
