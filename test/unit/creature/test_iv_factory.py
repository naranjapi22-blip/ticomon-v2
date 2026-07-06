from core.creature.iv_factory import IVFactory


def test_creates_valid_ivs():
    ivs = IVFactory.create()

    assert 0 <= ivs.hp <= 31
    assert 0 <= ivs.attack <= 31
    assert 0 <= ivs.defense <= 31
    assert 0 <= ivs.special_attack <= 31
    assert 0 <= ivs.special_defense <= 31
    assert 0 <= ivs.speed <= 31
