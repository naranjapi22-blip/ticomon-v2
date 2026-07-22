from dataclasses import replace

import pytest

from core.candy.candy_type import CandyType
from core.candy.reward_policy import RewardPolicy
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.species.variant import Variant
from infrastructure.species.evolution_chain_loader import build_evolution_chains
from test.factories import create_species


def test_stage_1_monotype_reward():
    species = create_species(
        id=4,
        name="Charmander",
        types=["fire"],
        evolution_species=[4, 5, 6],
    )

    creature = Creature(
        species=species,
        trainer_id=1,
        ivs=IVs(
            hp=0,
            attack=0,
            defense=0,
            special_attack=0,
            special_defense=0,
            speed=0,
        ),
        size=Size(1.0),
        nature=Nature("hardy"),
        is_shiny=False,
        current_form=None,
    )

    reward = RewardPolicy().reward_for(
        creature,
    )

    assert reward.get(CandyType.FIRE) == 2


def _creature_for(species):
    return Creature(
        species=species,
        trainer_id=1,
        ivs=IVs(0, 0, 0, 0, 0, 0),
        size=Size(1.0),
        nature=Nature("hardy"),
        is_shiny=False,
        current_form=None,
    )


@pytest.mark.parametrize(
    ("stage_species", "species_id", "expected"),
    [([1], 1, 2), ([1, 2], 2, 4), ([1, 2, 3], 3, 6)],
)
def test_reward_scales_by_evolution_stage(stage_species, species_id, expected):
    species = create_species(
        id=species_id,
        types=["fire"],
        evolution_species=stage_species,
    )

    reward = RewardPolicy().reward_for(_creature_for(species))

    assert reward.get(CandyType.FIRE) == expected


@pytest.mark.parametrize(
    ("stage_species", "species_id", "expected"),
    [([1], 1, 1), ([1, 2], 2, 2), ([1, 2, 3], 3, 3)],
)
def test_dual_type_reward_preserves_stage_total(stage_species, species_id, expected):
    species = create_species(
        id=species_id,
        types=["fire", "flying"],
        evolution_species=stage_species,
    )

    reward = RewardPolicy().reward_for(_creature_for(species))

    assert reward.get(CandyType.FIRE) == expected
    assert reward.get(CandyType.FLYING) == expected


def test_missing_chain_defaults_to_stage_one():
    species = replace(create_species(id=1), evolution_chain=None)

    assert (
        RewardPolicy().reward_for(_creature_for(species)).get(CandyType.ELECTRIC) == 2
    )


def test_branched_chain_uses_depth_from_the_root():
    chains = build_evolution_chains(
        [
            {"from_species_id": 1, "to_species_id": 2, "tier": "basic"},
            {"from_species_id": 2, "to_species_id": 3, "tier": "basic"},
            {"from_species_id": 2, "to_species_id": 4, "tier": "basic"},
        ]
    )

    assert chains[1].stage_of(1) == 1
    assert chains[2].stage_of(2) == 2
    assert chains[3].stage_of(3) == 3
    assert chains[4].stage_of(4) == 3


def test_invalid_chain_membership_defaults_to_stage_one():
    species = create_species(id=99, evolution_species=[1, 2, 3])

    assert (
        RewardPolicy().reward_for(_creature_for(species)).get(CandyType.ELECTRIC) == 2
    )


@pytest.mark.parametrize("types", [[], ["fire", "water", "grass"], ["unknown"]])
def test_invalid_types_fail_clearly(types):
    species = create_species(id=1, types=types)

    with pytest.raises(ValueError):
        RewardPolicy().reward_for(_creature_for(species))


def test_duplicate_types_are_normalized_to_one_type():
    species = create_species(id=1, types=["fire", "fire"])

    reward = RewardPolicy().reward_for(_creature_for(species))

    assert list(reward.items()) == [(CandyType.FIRE, 2)]


def test_visual_variant_keeps_the_canonical_species_stage():
    species = create_species(
        id=2,
        types=["fire"],
        evolution_species=[1, 2],
    )
    creature = replace(_creature_for(species), current_form=Variant(20, "alolan"))

    assert RewardPolicy().reward_for(creature).get(CandyType.FIRE) == 4
