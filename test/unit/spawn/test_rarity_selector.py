from core.spawn.rarity_selector import RaritySelector
from core.spawn.spawn_rarity import SpawnRarity


def test_returns_spawn_rarity():
    selector = RaritySelector()

    rarity = selector.select()

    assert isinstance(rarity, SpawnRarity)


def test_never_returns_none():
    selector = RaritySelector()

    rarity = selector.select()

    assert rarity is not None


def test_all_results_are_valid_spawn_rarities():
    selector = RaritySelector()

    results = [selector.select() for _ in range(1000)]

    assert set(results).issubset(set(SpawnRarity))
