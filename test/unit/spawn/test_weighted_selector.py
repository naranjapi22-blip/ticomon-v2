import pytest

from core.spawn.weighted_selector import WeightedSelector
from test.factories import create_species


def create_species_pool(amount: int):
    return tuple(
        create_species(
            id=i,
            name=f"pokemon_{i}",
        )
        for i in range(amount)
    )


def test_returns_empty_tuple_when_amount_is_zero():
    selector = WeightedSelector()
    species = create_species_pool(5)

    result = selector.select(
        species=species,
        amount=0,
    )

    assert result == ()


def test_returns_empty_tuple_when_amount_is_negative():
    selector = WeightedSelector()
    species = create_species_pool(5)

    result = selector.select(
        species=species,
        amount=-1,
    )

    assert result == ()


def test_raises_error_when_requesting_more_species_than_available():
    selector = WeightedSelector()
    species = create_species_pool(2)

    with pytest.raises(ValueError):
        selector.select(
            species=species,
            amount=3,
        )


def test_returns_requested_amount_of_species():
    selector = WeightedSelector()
    species = create_species_pool(10)

    result = selector.select(
        species=species,
        amount=3,
    )

    assert len(result) == 3


def test_returns_only_species_from_original_collection():
    selector = WeightedSelector()
    species = create_species_pool(10)

    result = selector.select(
        species=species,
        amount=4,
    )

    for selected in result:
        assert selected in species


def test_never_returns_duplicate_species():
    selector = WeightedSelector()
    species = create_species_pool(10)

    result = selector.select(
        species=species,
        amount=5,
    )

    assert len({species.id for species in result}) == len(result)
