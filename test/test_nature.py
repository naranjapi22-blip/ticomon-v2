from core.creature.nature import Nature
from core.creature.stat import Stat


def test_adamant_modifiers():
    nature = Nature("adamant")

    assert nature.modifier_for(Stat.ATTACK) == 1.1
    assert nature.modifier_for(Stat.SP_ATTACK) == 0.9
    assert nature.modifier_for(Stat.DEFENSE) == 1.0
    assert nature.modifier_for(Stat.SP_DEFENSE) == 1.0
    assert nature.modifier_for(Stat.SPEED) == 1.0


def test_modest_modifiers():
    nature = Nature("modest")

    assert nature.modifier_for(Stat.SP_ATTACK) == 1.1
    assert nature.modifier_for(Stat.ATTACK) == 0.9


def test_timid_modifiers():
    nature = Nature("timid")

    assert nature.modifier_for(Stat.SPEED) == 1.1
    assert nature.modifier_for(Stat.ATTACK) == 0.9


def test_unknown_nature():
    import pytest

    with pytest.raises(ValueError):
        Nature("pikachu")