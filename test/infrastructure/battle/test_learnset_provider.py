from core.battle.ports.damage_calculator import SpeciesLearnsetQuery
from core.species.regional_species import REGIONAL_POKEAPI_IDS
from infrastructure.battle.poke_env.learnset_provider import PokeEnvLearnsetProvider
from infrastructure.battle.poke_env.showdown_species_resolver import resolve_showdown_id


def test_resolve_showdown_id_uses_pokeapi_id_for_base_species():
    showdown_id = resolve_showdown_id(
        pokeapi_id=466,
        species_name="electivire",
    )

    assert showdown_id == "electivire"


def test_resolve_showdown_id_uses_regional_name_for_regional_pokeapi_id():
    regional_id = next(iter(REGIONAL_POKEAPI_IDS))

    showdown_id = resolve_showdown_id(
        pokeapi_id=regional_id,
        species_name="yamask-galar",
    )

    assert showdown_id == "yamaskgalar"


def test_learnset_provider_uses_species_query_not_name_only():
    provider = PokeEnvLearnsetProvider()

    learnset = provider.get_learnset(
        SpeciesLearnsetQuery(
            species_id=466,
            pokeapi_id=466,
            species_name="electivire",
        ),
    )

    assert learnset.species_showdown_id == "electivire"
    assert "thunderbolt" in learnset.moves or "wildcharge" in learnset.moves


def test_learnset_provider_distinguishes_yamask_and_galar_form():
    provider = PokeEnvLearnsetProvider()

    base = provider.get_learnset(
        SpeciesLearnsetQuery(
            species_id=562,
            pokeapi_id=562,
            species_name="yamask",
        ),
    )
    galar = provider.get_learnset(
        SpeciesLearnsetQuery(
            species_id=1057,
            pokeapi_id=10179,
            species_name="yamask-galar",
        ),
    )

    assert base.species_showdown_id == "yamask"
    assert galar.species_showdown_id == "yamaskgalar"
    assert base.moves != galar.moves
