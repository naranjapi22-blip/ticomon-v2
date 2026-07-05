from core.creature.base_stats import BaseStats
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.stat import Stat
from core.species.evolution_chain import EvolutionChain
from core.species.species import Species
from core.stats.stat_calculator import StatCalculator


def test_calculates_attack_stat_from_base_stats_ivs_and_nature():
    species = Species(
        id=1,
        name="Bulbasaur",
        generation=1,
        habitat="grassland",
        is_baby=False,
        is_legendary=False,
        is_mythical=False,
        types=["grass", "poison"],
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
        forms_switchable=False,
        evolution_chain=EvolutionChain(
            id=1,
            species=[],
            candy_requirements={},
        ),
        variants=[],
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
        size=1.0,
        current_form=None,
    )

    calculator = StatCalculator()

    attack = calculator.calculate(
        creature,
        Stat.ATTACK,
    )

    assert attack == 75