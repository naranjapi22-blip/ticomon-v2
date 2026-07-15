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


def test_lowercase_greninja_returns_normal_form_when_chance_does_not_trigger():
    species = create_species(
        id=658,
        name="greninja",
        variants=[Variant(id=128, name="ash")],
    )

    with patch("random.random", return_value=0.005):
        assert VariantFactory.create(species) is None


def test_lowercase_greninja_returns_ash_when_chance_triggers():
    species = create_species(
        id=658,
        name="greninja",
        variants=[Variant(id=128, name="ash")],
    )

    with patch("random.random", return_value=0.0049):
        variant = VariantFactory.create(species)

    assert variant == Variant(id=128, name="ash")


def test_pikachu_probability_is_case_and_whitespace_insensitive():
    species = create_species(
        id=25,
        name="  pIkAcHu  ",
        variants=[Variant(id=1, name="Rockstar")],
    )

    with patch("random.random", return_value=0.005):
        assert VariantFactory.create(species) is None

    with patch("random.random", return_value=0.0049):
        assert VariantFactory.create(species) == Variant(id=1, name="Rockstar")


def test_species_without_special_probability_keeps_random_variant_behavior():
    species = create_species(
        id=133,
        name="eevee",
        variants=[Variant(id=2, name="Partner")],
    )

    with patch("random.choice", return_value=species.variants[0]) as choice:
        variant = VariantFactory.create(species)

    assert variant == species.variants[0]
    choice.assert_called_once_with(species.variants)
