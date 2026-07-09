from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.evolution.evolution_failure_reason import EvolutionFailureReason
from core.evolution.evolution_policy import EvolutionPolicy
from test.builders.creature_builder import CreatureBuilder
from test.builders.evolution_builder import EvolutionBuilder
from test.builders.species_builder import SpeciesBuilder


def test_validate_success():

    creature = CreatureBuilder().build()

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                25,
            )
        )
    )

    result = EvolutionPolicy().validate(
        creature,
        inventory,
    )

    assert result.success
    assert result.failure_reason is None
    assert (
        result.consumed_candies.get(
            CandyType.FIRE,
        )
        == 25
    )


def test_validate_fails_when_trainer_has_not_enough_candies():

    creature = CreatureBuilder().build()

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                10,
            )
        )
    )

    result = EvolutionPolicy().validate(
        creature,
        inventory,
    )

    assert not result.success
    assert result.failure_reason == EvolutionFailureReason.NOT_ENOUGH_CANDIES


def test_validate_fails_when_creature_is_final_stage():

    chain = (
        EvolutionBuilder()
        .with_species(
            [1, 2],
        )
        .build()
    )

    species = (
        SpeciesBuilder()
        .with_id(2)
        .with_evolution_chain(
            chain,
        )
        .build()
    )

    creature = (
        CreatureBuilder()
        .with_species(
            species,
        )
        .build()
    )

    inventory = CandyInventory()

    result = EvolutionPolicy().validate(
        creature,
        inventory,
    )

    assert not result.success
    assert result.failure_reason == EvolutionFailureReason.FINAL_STAGE
