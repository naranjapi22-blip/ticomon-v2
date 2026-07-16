from core.creature.base_stats import BaseStats
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.creature.stat import Stat
from core.stats.stat_calculator import StatCalculator
from test.factories import create_species


def test_calculates_attack_stat_from_base_stats_ivs_and_nature():
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
        nature=Nature("adamant"),
        is_shiny=False,
        size=Size(1.0),
        current_form=None,
    )

    calculator = StatCalculator()

    attack = calculator.calculate(
        creature,
        Stat.ATTACK,
    )

    assert attack == 75


def test_calculates_stats_with_minted_nature_but_not_hp_modifier():
    species = create_species(
        id=1,
        name="Bulbasaur",
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
        nature=Nature("modest"),
        minted_nature=Nature("adamant"),
        is_shiny=False,
        size=Size(1.0),
        current_form=None,
    )

    calculator = StatCalculator()

    assert calculator.calculate(creature, Stat.ATTACK) == 75
    assert calculator.calculate(creature, Stat.HP) == 120
