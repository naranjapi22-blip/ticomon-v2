import pytest

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.evolution.evolution_cost_policy import EvolutionCostPolicy
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_service import EvolutionService
from core.species.variant import Variant
from test.builders.creature_builder import CreatureBuilder
from test.builders.evolution_rule_builder import EvolutionRuleBuilder
from test.builders.species_builder import SpeciesBuilder
from test.factories import create_species
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


@pytest.mark.asyncio
async def test_evolve_preserves_a_matching_canonical_variant():
    source_variant = Variant(105, "blue")
    middle_variant = Variant(109, "blue")
    target_variant = Variant(114, "blue")
    first = create_species(
        id=669,
        name="flabebe",
        types=["fairy"],
        variants=[source_variant],
    )
    second = create_species(
        id=670,
        name="floette",
        types=["fairy"],
        variants=[middle_variant],
    )
    third = create_species(
        id=671,
        name="florges",
        types=["fairy"],
        variants=[target_variant],
    )
    first_rule = (
        EvolutionRuleBuilder()
        .with_from_species(669)
        .with_to_species(670)
        .with_candy_type(CandyType.FAIRY)
        .with_tier("basic")
        .build()
    )
    second_rule = (
        EvolutionRuleBuilder()
        .with_from_species(670)
        .with_to_species(671)
        .with_candy_type(CandyType.FAIRY)
        .with_tier("standard")
        .build()
    )
    service = EvolutionService(
        policy=EvolutionPolicy(cost_policy=EvolutionCostPolicy()),
        species_repository=FakeSpeciesRepository(first, second, third),
    )
    creature = CreatureBuilder().with_species(first).build()
    creature.current_form = source_variant
    inventory = CandyInventory()
    inventory.add(CandyBundle.from_amounts(CandyAmount(CandyType.FAIRY, 30)))

    result = await service.evolve(creature, inventory, first_rule)

    assert result.success
    assert creature.species is second
    assert creature.current_form == middle_variant

    result = await service.evolve(creature, inventory, second_rule)

    assert result.success
    assert creature.species is third
    assert creature.current_form == target_variant
