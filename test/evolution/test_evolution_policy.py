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
from core.evolution.evolution_failure_reason import EvolutionFailureReason
from core.evolution.evolution_policy import EvolutionPolicy
from core.rarity import Rarity
from core.species.species import Species
from core.species.species_metadata import SpeciesMetadata


def make_species(
    species_id: int,
    evolution_chain: EvolutionChain | None = None,
) -> Species:
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
        evolution_chain=evolution_chain
        or EvolutionChain(
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


def test_validate_success():

    creature = make_creature()

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
    assert result.consumed_candies.get(CandyType.FIRE) == 25


def test_validate_fails_when_trainer_has_not_enough_candies():

    creature = make_creature()

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

    chain = EvolutionChain(
        id=1,
        species=[1, 2],
        candy_requirements={
            1: 25,
        },
    )

    creature = make_creature(
        make_species(
            2,
            evolution_chain=chain,
        ),
    )

    inventory = CandyInventory()

    result = EvolutionPolicy().validate(
        creature,
        inventory,
    )

    assert not result.success
    assert result.failure_reason == EvolutionFailureReason.FINAL_STAGE
