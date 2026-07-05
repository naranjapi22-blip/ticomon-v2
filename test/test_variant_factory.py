from unittest.mock import patch

from core.species.variant import Variant
from core.creature.variant_factory import VariantFactory
from core.species.evolution_chain import EvolutionChain
from core.species.species import Species


def test_create_variant():

    chain = EvolutionChain(
        id=1,
        species=[],
        candy_requirements={}
    )

    species = Species(
        id=25,
        name="Pikachu",
        generation=1,
        habitat="Forest",
        is_baby=False,
        is_legendary=False,
        is_mythical=False,
        types=["Electric"],
        base_stats={},
        height=4,
        weight=60,
        capture_rate=190,
        forms_switchable=False,
        evolution_chain=chain,
        variants=[
            Variant(id=1, name="Rockstar"),
            Variant(id=2, name="Libre"),
        ],
    )

    with patch("random.random", return_value=0.0):
        variant = VariantFactory.create(species)

    assert variant is not None
    assert variant.name in ("Rockstar", "Libre")


def test_create_without_variants():

    chain = EvolutionChain(
        id=1,
        species=[],
        candy_requirements={}
    )

    species = Species(
        id=1,
        name="Bulbasaur",
        generation=1,
        habitat="Grassland",
        is_baby=False,
        is_legendary=False,
        is_mythical=False,
        types=["Grass"],
        base_stats={},
        height=7,
        weight=69,
        capture_rate=45,
        forms_switchable=False,
        evolution_chain=chain,
        variants=[],
    )

    assert VariantFactory.create(species) is None