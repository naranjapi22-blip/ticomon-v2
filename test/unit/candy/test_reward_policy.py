from core.candy.candy_type import CandyType
from core.candy.reward_policy import RewardPolicy
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
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
        variant=None,
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
