from core.creature.shiny_factory import ShinyFactory


def test_creates_boolean():
    shiny = ShinyFactory.create()

    assert isinstance(shiny, bool)
