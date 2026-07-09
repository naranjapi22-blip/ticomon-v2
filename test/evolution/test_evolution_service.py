import pytest

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.evolution.evolution_cost_policy import EvolutionCostPolicy
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_service import EvolutionService
from test.builders.creature_builder import CreatureBuilder
from test.builders.evolution_rule_builder import EvolutionRuleBuilder
from test.builders.species_builder import SpeciesBuilder
from test.fakes.fake_species_repository import (
    FakeSpeciesRepository,
)


def create_service(
    rule,
    first_species,
    second_species,
):
    return EvolutionService(
        policy=EvolutionPolicy(
            cost_policy=EvolutionCostPolicy(),
        ),
        species_repository=FakeSpeciesRepository(
            first_species,
            second_species,
        ),
    )


@pytest.mark.asyncio
async def test_evolve_changes_species_and_consumes_candies():

    first = SpeciesBuilder().with_id(1).build()

    second = SpeciesBuilder().with_id(2).build()

    rule = (
        EvolutionRuleBuilder()
        .with_from_species(
            1,
        )
        .with_to_species(
            2,
        )
        .with_candy_type(
            CandyType.FIRE,
        )
        .with_tier(
            "basic",
        )
        .build()
    )

    service = create_service(
        rule,
        first,
        second,
    )

    creature = (
        CreatureBuilder()
        .with_species(
            first,
        )
        .build()
    )

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                10,
            )
        )
    )

    result = await service.evolve(
        creature,
        inventory,
        rule,
    )
    assert result.success
    assert creature.species.id == 2

    assert (
        inventory.get_amount(
            CandyType.FIRE,
        )
        == 0
    )


@pytest.mark.asyncio
async def test_evolve_does_not_change_species_when_no_candies():

    first = SpeciesBuilder().with_id(1).build()

    second = SpeciesBuilder().with_id(2).build()

    rule = (
        EvolutionRuleBuilder()
        .with_from_species(
            1,
        )
        .with_to_species(
            2,
        )
        .build()
    )

    service = create_service(
        rule,
        first,
        second,
    )

    creature = (
        CreatureBuilder()
        .with_species(
            first,
        )
        .build()
    )

    inventory = CandyInventory()

    result = await service.evolve(
        creature,
        inventory,
        rule,
    )

    assert not result.success
    assert creature.species.id == 1


@pytest.mark.asyncio
async def test_evolve_returns_new_species():

    first = SpeciesBuilder().with_id(1).build()

    second = SpeciesBuilder().with_id(2).build()

    rule = (
        EvolutionRuleBuilder()
        .with_from_species(
            1,
        )
        .with_to_species(
            2,
        )
        .build()
    )

    service = create_service(
        rule,
        first,
        second,
    )

    creature = (
        CreatureBuilder()
        .with_species(
            first,
        )
        .build()
    )

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                10,
            )
        )
    )

    result = await service.evolve(
        creature,
        inventory,
        rule,
    )

    assert result.previous_species.id == 1
    assert result.evolved_species.id == 2
