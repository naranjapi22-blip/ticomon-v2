from core.species.variant import Variant


def test_variant():
    variant = Variant(
        id=1,
        name="Rockstar",
    )

    assert variant.id == 1
    assert variant.name == "Rockstar"