from core.creature.base_stats import BaseStats
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.creature.stat import Stat
from test.factories import create_species


def test_creature_returns_base_stat():
    species = create_species(
        id=1,
        name="Bulbasaur",
        types=["grass", "poison"],
        capture_rate=45,
        base_stats=BaseStats(
            hp=45,
            attack=49,
            defense=49,
            special_attack=65,
            special_defense=65,
            speed=45,
        ),
    )

    creature = Creature(
        id=1,
        species=species,
        trainer_id=1,
        ivs=IVs(
            hp=31,
            attack=31,
            defense=31,
            special_attack=31,
            special_defense=31,
            speed=31,
        ),
        nature=Nature("hardy"),
        is_shiny=False,
        size=Size(1.0),
        current_form=None,
    )

    assert creature.stat_for(Stat.ATTACK) == 49
    assert creature.original_trainer_id == 1
