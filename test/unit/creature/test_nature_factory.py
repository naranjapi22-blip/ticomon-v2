from core.creature.nature import Nature
from core.creature.nature_factory import NatureFactory


def test_creates_valid_nature():
    nature = NatureFactory.create()

    assert isinstance(nature, Nature)
