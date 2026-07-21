from types import SimpleNamespace
from unittest.mock import Mock

from infrastructure.battle.poke_env import loadout_catalog as module
from infrastructure.battle.poke_env.loadout_catalog import PokeEnvLoadoutCatalog


def test_ability_catalog_prioritizes_short_effect_and_caches_lookup(monkeypatch):
    module._ability_effect.cache_clear()
    data = SimpleNamespace(
        pokedex={
            "minun": {"abilities": {"0": "Static"}},
        },
        learnset={},
    )
    monkeypatch.setattr(module, "_gen9_data", lambda: data)
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "effect_entries": [
                {
                    "language": {"name": "en"},
                    "effect": "Long official effect.",
                    "short_effect": "Short official effect.",
                }
            ]
        },
    )
    get = Mock(return_value=response)
    monkeypatch.setattr(module.requests, "get", get)
    catalog = PokeEnvLoadoutCatalog()
    species = SimpleNamespace(pokeapi_id=312, name="Minun")

    first = catalog.abilities_for(species)
    second = catalog.abilities_for(species)

    assert first[0].effect == "Short official effect."
    assert second[0].effect == first[0].effect
    assert get.call_count == 1
    module._ability_effect.cache_clear()
