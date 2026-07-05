from core.creature.base_stats import BaseStats
from core.creature.stat import Stat


def test_returns_the_value_for_each_stat():
    base_stats = BaseStats(
        hp=45,
        attack=49,
        defense=49,
        special_attack=65,
        special_defense=65,
        speed=45,
    )

    assert base_stats.for_stat(Stat.HP) == 45
    assert base_stats.for_stat(Stat.ATTACK) == 49
    assert base_stats.for_stat(Stat.DEFENSE) == 49
    assert base_stats.for_stat(Stat.SP_ATTACK) == 65
    assert base_stats.for_stat(Stat.SP_DEFENSE) == 65
    assert base_stats.for_stat(Stat.SPEED) == 45