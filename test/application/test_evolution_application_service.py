import pytest

from application.evolution.evolution_application_service import (
    EvolutionApplicationService,
)
from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.evolution.evolution_cost_policy import (
    EvolutionCostPolicy,
)
from core.evolution.evolution_policy import (
    EvolutionPolicy,
)
from core.evolution.evolution_service import (
    EvolutionService,
)
from test.builders.creature_builder import (
    CreatureBuilder,
)
from test.builders.evolution_rule_builder import (
    EvolutionRuleBuilder,
)
from test.builders.species_builder import (
    SpeciesBuilder,
)
from test.fakes.fake_candy_repository import (
    FakeCandyRepository,
)
from test.fakes.fake_creature_repository import (
    FakeCreatureRepository,
)
from test.fakes.fake_evolution_repository import (
    FakeEvolutionRepository,
)
from test.fakes.fake_species_repository import (
    FakeSpeciesRepository,
)


@pytest.mark.asyncio
async def test_evolution_application_service_evolves_creature():

    first_species = SpeciesBuilder().with_id(1).build()

    second_species = SpeciesBuilder().with_id(2).build()

    creature = (
        CreatureBuilder()
        .with_species(
            first_species,
        )
        .build()
    )

    creature_repository = FakeCreatureRepository(
        creature,
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

    candy_repository = FakeCandyRepository(
        inventory,
    )

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

    service = EvolutionApplicationService(
        evolution_service=EvolutionService(
            policy=EvolutionPolicy(
                cost_policy=EvolutionCostPolicy(),
            ),
            evolution_repository=FakeEvolutionRepository(
                rule,
            ),
            species_repository=FakeSpeciesRepository(
                first_species,
                second_species,
            ),
        ),
        creature_repository=creature_repository,
        candy_repository=candy_repository,
    )

    result = await service.evolve(
        trainer_id=1,
        creature_id=creature.id,
    )

    assert result.success

    assert result.creature.species.id == 2

    assert result.evolved_species.id == 2

    assert (
        inventory.get_amount(
            CandyType.FIRE,
        )
        == 0
    )

    assert (
        len(
            creature_repository.saved,
        )
        == 1
    )

    assert (
        len(
            candy_repository.saved,
        )
        == 1
    )
