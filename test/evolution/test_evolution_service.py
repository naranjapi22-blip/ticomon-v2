import pytest

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.creature.base_stats import BaseStats
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.evolution.evolution_chain import EvolutionChain
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_service import EvolutionService
from core.rarity import Rarity
from core.species.species import Species
from core.species.species_metadata import SpeciesMetadata
from core.species.species_repository import SpeciesRepository


def make_species(species_id: int) -> Species:
    return Species(
        id=species_id,
        name=f"Species {species_id}",
        types=["fire"],
        base_stats=BaseStats(
            hp=45,
            attack=49,
            defense=49,
            special_attack=65,
            special_defense=65,
            speed=45,
        ),
        height=7,
        weight=69,
        capture_rate=45,
        spawn_rarity=Rarity.COMMON,
        metadata=SpeciesMetadata(
            generation=1,
            is_baby=False,
            is_legendary=False,
            is_mythical=False,
        ),
        evolution_chain=EvolutionChain(
            id=1,
            species=[1, 2],
            candy_requirements={
                1: 25,
            },
        ),
    )


def make_creature(
    species: Species | None = None,
) -> Creature:
    return Creature(
        species=species or make_species(1),
        variant=None,
        trainer_id=1,
        ivs=IVs(
            hp=31,
            attack=31,
            defense=31,
            special_attack=31,
            special_defense=31,
            speed=31,
        ),
        size=Size(1.0),
        nature=Nature("hardy"),
        is_shiny=False,
        current_form=None,
    )


class FakeSpeciesRepository(SpeciesRepository):

    def __init__(
        self,
        *species: Species,
    ) -> None:
        self._species = {s.id: s for s in species}

    async def get(
        self,
        species_id: int,
    ) -> Species:
        return self._species[species_id]

    async def find_by_name(
        self,
        name: str,
    ) -> Species | None:
        raise NotImplementedError

    async def get_all(
        self,
    ):
        raise NotImplementedError

    async def find_by_spawn_rarity(
        self,
        rarity,
    ):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_evolve_changes_species_and_consumes_candies():

    first = make_species(1)
    second = make_species(2)

    service = EvolutionService(
        policy=EvolutionPolicy(),
        species_repository=FakeSpeciesRepository(
            first,
            second,
        ),
    )

    creature = make_creature(first)

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                25,
            )
        )
    )

    result = await service.evolve(
        creature,
        inventory,
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
async def test_evolve_does_not_change_species_when_validation_fails():

    first = make_species(1)
    second = make_species(2)

    service = EvolutionService(
        policy=EvolutionPolicy(),
        species_repository=FakeSpeciesRepository(
            first,
            second,
        ),
    )

    creature = make_creature(first)

    inventory = CandyInventory()

    result = await service.evolve(
        creature,
        inventory,
    )

    assert not result.success
    assert creature.species.id == 1


@pytest.mark.asyncio
async def test_evolve_returns_new_species():

    first = make_species(1)
    second = make_species(2)

    service = EvolutionService(
        policy=EvolutionPolicy(),
        species_repository=FakeSpeciesRepository(
            first,
            second,
        ),
    )

    creature = make_creature(first)

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                25,
            )
        )
    )

    result = await service.evolve(
        creature,
        inventory,
    )

    assert result.previous_species.id == 1
    assert result.evolved_species.id == 2
