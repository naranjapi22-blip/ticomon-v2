from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import interfaces.discord.buttons.evolution_button as evolution_button_module
from core.candy.candy_type import CandyType
from core.evolution.evolution_rule import EvolutionRule
from interfaces.discord.buttons.evolution_button import EvolutionButton
from interfaces.discord.views.evolution_confirm_view import EvolutionConfirmView
from interfaces.discord.views.evolution_view import EvolutionView


def _interaction() -> SimpleNamespace:
    return SimpleNamespace(
        response=SimpleNamespace(
            defer=AsyncMock(),
            send_message=AsyncMock(),
            is_done=Mock(return_value=False),
        ),
        edit_original_response=AsyncMock(),
    )


def _view(core) -> EvolutionView:
    return EvolutionView(core, trainer_id=1, collection_number=7, options=[])


def _rule() -> EvolutionRule:
    return EvolutionRule(
        from_species_id=1,
        to_species_id=2,
        candy_type=CandyType.FIRE,
        tier="basic",
    )


def _result() -> SimpleNamespace:
    return SimpleNamespace(success=True, achievements=())


@pytest.mark.asyncio
async def test_evolution_button_defers_before_evolve_and_edits_original(monkeypatch):
    events = []

    async def evolve(**_kwargs):
        events.append("evolve")
        return _result()

    core = SimpleNamespace(
        evolution_application=SimpleNamespace(evolve=evolve),
    )
    view = _view(core)
    button = EvolutionButton(core, 1, 7, _rule(), "Ivysaur")
    view.add_item(button)
    interaction = _interaction()
    interaction.response.defer.side_effect = lambda: events.append("defer")
    edit_result = AsyncMock(side_effect=lambda **_kwargs: events.append("edit"))
    monkeypatch.setattr(evolution_button_module, "edit_evolution_result", edit_result)

    await button.callback(interaction)

    assert events == ["defer", "evolve", "edit"]
    interaction.response.send_message.assert_not_awaited()
    interaction.edit_original_response.assert_not_awaited()
    edit_result.assert_awaited_once()
    assert all(child.disabled for child in view.children)


@pytest.mark.asyncio
async def test_evolution_button_expected_failure_edits_deferred_response():
    evolve = AsyncMock(return_value=SimpleNamespace(success=False))
    core = SimpleNamespace(evolution_application=SimpleNamespace(evolve=evolve))
    view = _view(core)
    button = EvolutionButton(core, 1, 7, _rule(), "Ivysaur")
    view.add_item(button)
    interaction = _interaction()

    await button.callback(interaction)

    interaction.response.defer.assert_awaited_once()
    interaction.edit_original_response.assert_awaited_once_with(
        content="❌ Evolution failed.",
        view=None,
    )
    interaction.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_evolution_button_unexpected_failure_is_logged_and_responded(caplog):
    evolve = AsyncMock(side_effect=RuntimeError("database unavailable"))
    core = SimpleNamespace(evolution_application=SimpleNamespace(evolve=evolve))
    view = _view(core)
    button = EvolutionButton(core, 1, 7, _rule(), "Ivysaur")
    view.add_item(button)
    interaction = _interaction()

    await button.callback(interaction)

    assert "evolution button failed" in caplog.text
    interaction.response.defer.assert_awaited_once()
    interaction.edit_original_response.assert_awaited_once_with(
        content="❌ Evolution failed. Please try again later.",
        view=None,
    )


@pytest.mark.asyncio
async def test_evolution_button_ignores_double_click(monkeypatch):
    evolve = AsyncMock(return_value=_result())
    core = SimpleNamespace(evolution_application=SimpleNamespace(evolve=evolve))
    view = _view(core)
    button = EvolutionButton(core, 1, 7, _rule(), "Ivysaur")
    view.add_item(button)
    monkeypatch.setattr(
        evolution_button_module,
        "edit_evolution_result",
        AsyncMock(),
    )
    first = _interaction()
    second = _interaction()

    await button.callback(first)
    await button.callback(second)

    evolve.assert_awaited_once()
    second.response.send_message.assert_awaited_once_with(
        "Evolution is already being processed.",
        ephemeral=True,
    )
    second.response.defer.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_button_defers_before_evolve(monkeypatch):
    evolve = AsyncMock(return_value=_result())
    core = SimpleNamespace(evolution_application=SimpleNamespace(evolve=evolve))
    view = EvolutionConfirmView(core, 1, 7, _rule())
    button = view.children[0]
    interaction = _interaction()
    edit_result = AsyncMock()
    monkeypatch.setattr(
        "interfaces.discord.buttons.evolution_confirm_button.edit_evolution_result",
        edit_result,
    )

    await button.callback(interaction)

    interaction.response.defer.assert_awaited_once()
    evolve.assert_awaited_once()
    edit_result.assert_awaited_once()
