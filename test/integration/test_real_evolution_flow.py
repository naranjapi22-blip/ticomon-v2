import pytest

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
from infrastructure.evolution.neon_evolution_repository import (
    NeonEvolutionRepository,
)
from infrastructure.species.neon_species_repository import (
    NeonSpeciesRepository,
)
from test.builders.creature_builder import (
    CreatureBuilder,
)


@pytest.mark.asyncio
async def test_real_evolution_flow_bulbasaur_to_ivysaur():

    species_repository = NeonSpeciesRepository()

    evolution_repository = NeonEvolutionRepository()

    bulbasaur = await species_repository.get(
        1,
    )

    ivysaur = await species_repository.get(
        2,
    )

    creature = (
        CreatureBuilder()
        .with_species(
            bulbasaur,
        )
        .build()
    )

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.GRASS,
                10,
            )
        )
    )

    service = EvolutionService(
        policy=EvolutionPolicy(
            cost_policy=EvolutionCostPolicy(),
        ),
        evolution_repository=evolution_repository,
        species_repository=species_repository,
    )

    result = await service.evolve(
        creature,
        inventory,
    )

    assert result.success

    assert creature.species.id == ivysaur.id

    assert creature.species.name == "ivysaur"

    assert (
        inventory.get_amount(
            CandyType.GRASS,
        )
        == 0
    )
