from unittest.mock import patch

from core.creature.variant_factory import VariantFactory
from core.species.variant import Variant
from test.factories import create_species


def test_create_variant():
    species = create_species(
        id=25,
        name="Pikachu",
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
    species = create_species(
        id=1,
        name="Bulbasaur",
        types=["grass"],
        capture_rate=45,
        variants=[],
    )

    assert VariantFactory.create(species) is None
